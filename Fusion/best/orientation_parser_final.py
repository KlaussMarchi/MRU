import math
import numpy as np
from scipy.signal import butter, filtfilt
from scipy.spatial.transform import Rotation, Slerp
from scipy.optimize import minimize


class OrientationParser:
    """
    IMU sensor fusion (gyro + accel) with quaternion-based orientation estimation
    and heave computation. Uses a forward-backward smoothing approach to
    eliminate initialization transient and reduce phase lag.

    Supports Madgwick (fixed/adaptive beta) and Mahony filter backends.
    Includes a mounting-rotation correction to align sensor body frame
    to the reference frame.

    Input units:
      - Gyro: deg/s
      - Accel: m/s^2
    Output:
      - Euler angles (pitch, roll, yaw) in degrees, intrinsic XYZ convention
      - Heave (vertical displacement) in meters
    """

    GRAVITY = 9.80665
    DEG2RAD = math.pi / 180.0

    def __init__(self, method='madgwick_adapt', beta=0.02, betaMin=0.001,
                 betaMax=0.1, adaptRate=10.0, accelMin=0.5, accelMax=19.6,
                 kp=1.0, ki=0.0,
                 mountRoll=180.0, mountPitch=0.0, mountYaw=0.0,
                 hpCutoff=0.1, hpOrder=2, heaveGain=1.0,
                 smoothAlpha=0.5, initSamples=10,
                 dt=0.1):

        self.method = method
        self.beta = beta
        self.betaMin = betaMin
        self.betaMax = betaMax
        self.adaptRate = adaptRate
        self.accelMin = accelMin
        self.accelMax = accelMax
        self.kp = kp
        self.ki = ki
        self.mountRoll = mountRoll
        self.mountPitch = mountPitch
        self.mountYaw = mountYaw
        self.hpCutoff = hpCutoff
        self.hpOrder = hpOrder
        self.heaveGain = heaveGain
        self.smoothAlpha = smoothAlpha
        self.initSamples = initSamples
        self.dt = dt

        mr = mountRoll * self.DEG2RAD
        mp = mountPitch * self.DEG2RAD
        my = mountYaw * self.DEG2RAD
        self.mountRot = Rotation.from_euler('xyz', [mr, mp, my])

    def _normalizeQ(self, q):
        n = np.linalg.norm(q)
        if n < 1e-10:
            return np.array([1.0, 0.0, 0.0, 0.0])
        return q / n

    def _initFromAccel(self, accelData, nSamples):
        n = min(nSamples, len(accelData))
        ax = np.mean(accelData[:n, 0])
        ay = np.mean(accelData[:n, 1])
        az = np.mean(accelData[:n, 2])

        norm = math.sqrt(ax * ax + ay * ay + az * az)
        if norm < self.accelMin:
            return np.array([1.0, 0.0, 0.0, 0.0])
        ax /= norm
        ay /= norm
        az /= norm

        pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az))
        roll = math.atan2(ay, az)

        cp = math.cos(pitch / 2.0)
        sp = math.sin(pitch / 2.0)
        cr = math.cos(roll / 2.0)
        sr = math.sin(roll / 2.0)

        q = np.array([cp * cr, cp * sr, sp * cr, -sp * sr])
        return self._normalizeQ(q)

    def _filterPass(self, gyroData, accelData, forward=True):
        n = len(gyroData)
        quats = np.zeros((n, 4))

        if forward:
            q = self._initFromAccel(accelData, self.initSamples)
            indices = range(n)
        else:
            q = self._initFromAccel(accelData[::-1], self.initSamples)
            indices = range(n - 1, -1, -1)

        integralFb = np.zeros(3)

        for count, i in enumerate(indices):
            gx = gyroData[i, 0] * self.DEG2RAD
            gy = gyroData[i, 1] * self.DEG2RAD
            gz = gyroData[i, 2] * self.DEG2RAD
            ax = accelData[i, 0]
            ay = accelData[i, 1]
            az = accelData[i, 2]

            if not forward:
                gx = -gx
                gy = -gy
                gz = -gz

            if self.method == 'madgwick':
                q, integralFb = self._madgwickStep(
                    q, integralFb, gx, gy, gz, ax, ay, az, self.beta)
            elif self.method == 'madgwick_adapt':
                aNorm = math.sqrt(ax * ax + ay * ay + az * az)
                accelDev = abs(aNorm - self.GRAVITY) / self.GRAVITY
                adaptBeta = self.betaMax * math.exp(-accelDev * self.adaptRate)
                adaptBeta = max(self.betaMin, min(self.betaMax, adaptBeta))
                q, integralFb = self._madgwickStep(
                    q, integralFb, gx, gy, gz, ax, ay, az, adaptBeta)
            elif self.method == 'mahony':
                q, integralFb = self._mahonyStep(
                    q, integralFb, gx, gy, gz, ax, ay, az)

            quats[i] = q

        return quats

    def _madgwickStep(self, q, integralFb, gx, gy, gz, ax, ay, az, beta):
        q0, q1, q2, q3 = q

        qDot1 = 0.5 * (-q1 * gx - q2 * gy - q3 * gz)
        qDot2 = 0.5 * (q0 * gx + q2 * gz - q3 * gy)
        qDot3 = 0.5 * (q0 * gy - q1 * gz + q3 * gx)
        qDot4 = 0.5 * (q0 * gz + q1 * gy - q2 * gx)

        aNorm = math.sqrt(ax * ax + ay * ay + az * az)
        if self.accelMin < aNorm < self.accelMax:
            inv = 1.0 / aNorm
            axn, ayn, azn = ax * inv, ay * inv, az * inv

            q0q0 = q0 * q0
            q1q1 = q1 * q1
            q2q2 = q2 * q2
            q3q3 = q3 * q3

            s0 = (4.0 * q0 * q2q2 + 2.0 * q2 * axn
                   + 4.0 * q0 * q1q1 - 2.0 * q1 * ayn)
            s1 = (4.0 * q1 * q3q3 - 2.0 * q3 * axn
                   + 4.0 * q0q0 * q1 - 2.0 * q0 * ayn
                   - 4.0 * q1 + 8.0 * q1 * q1q1
                   + 8.0 * q1 * q2q2 + 4.0 * q1 * azn)
            s2 = (4.0 * q0q0 * q2 + 2.0 * q0 * axn
                   + 4.0 * q2 * q3q3 - 2.0 * q3 * ayn
                   - 4.0 * q2 + 8.0 * q2 * q1q1
                   + 8.0 * q2 * q2q2 + 4.0 * q2 * azn)
            s3 = (4.0 * q1q1 * q3 - 2.0 * q1 * axn
                   + 4.0 * q2q2 * q3 - 2.0 * q2 * ayn)

            sNorm = math.sqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3)
            if sNorm > 1e-10:
                inv_s = 1.0 / sNorm
                qDot1 -= beta * s0 * inv_s
                qDot2 -= beta * s1 * inv_s
                qDot3 -= beta * s2 * inv_s
                qDot4 -= beta * s3 * inv_s

        newQ = np.array([
            q0 + qDot1 * self.dt,
            q1 + qDot2 * self.dt,
            q2 + qDot3 * self.dt,
            q3 + qDot4 * self.dt
        ])
        return self._normalizeQ(newQ), integralFb

    def _mahonyStep(self, q, integralFb, gx, gy, gz, ax, ay, az):
        q0, q1, q2, q3 = q

        aNorm = math.sqrt(ax * ax + ay * ay + az * az)
        if aNorm < self.accelMin or aNorm > self.accelMax:
            halfGx, halfGy, halfGz = gx, gy, gz
        else:
            inv = 1.0 / aNorm
            axn, ayn, azn = ax * inv, ay * inv, az * inv

            vx = 2.0 * (q1 * q3 - q0 * q2)
            vy = 2.0 * (q0 * q1 + q2 * q3)
            vz = q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3

            ex = ayn * vz - azn * vy
            ey = azn * vx - axn * vz
            ez = axn * vy - ayn * vx

            if self.ki > 0:
                integralFb = integralFb.copy()
                integralFb[0] += self.ki * ex * self.dt
                integralFb[1] += self.ki * ey * self.dt
                integralFb[2] += self.ki * ez * self.dt
            else:
                integralFb = np.zeros(3)

            halfGx = gx + self.kp * ex + integralFb[0]
            halfGy = gy + self.kp * ey + integralFb[1]
            halfGz = gz + self.kp * ez + integralFb[2]

        qDot1 = 0.5 * (-q1 * halfGx - q2 * halfGy - q3 * halfGz)
        qDot2 = 0.5 * (q0 * halfGx + q2 * halfGz - q3 * halfGy)
        qDot3 = 0.5 * (q0 * halfGy - q1 * halfGz + q3 * halfGx)
        qDot4 = 0.5 * (q0 * halfGz + q1 * halfGy - q2 * halfGx)

        newQ = np.array([
            q0 + qDot1 * self.dt,
            q1 + qDot2 * self.dt,
            q2 + qDot3 * self.dt,
            q3 + qDot4 * self.dt
        ])
        return self._normalizeQ(newQ), integralFb

    def _slerpQuats(self, qFwd, qBwd, alpha):
        n = len(qFwd)
        result = np.zeros((n, 4))
        for i in range(n):
            qf = qFwd[i]
            qb = qBwd[i]
            if np.dot(qf, qb) < 0:
                qb = -qb
            result[i] = self._normalizeQ((1.0 - alpha) * qf + alpha * qb)
        return result

    def _rotateToWorldBatch(self, quatsWxyz, accelData):
        n = len(quatsWxyz)
        quatsXyzw = np.column_stack([
            quatsWxyz[:, 1], quatsWxyz[:, 2],
            quatsWxyz[:, 3], quatsWxyz[:, 0]
        ])
        rotations = Rotation.from_quat(quatsXyzw)
        worldAccel = rotations.apply(accelData)
        return worldAccel[:, 2]

    def process(self, gyroData, accelData):
        n = len(gyroData)

        quatsFwd = self._filterPass(gyroData, accelData, forward=True)
        quatsBwd = self._filterPass(gyroData, accelData, forward=False)
        quatsSmooth = self._slerpQuats(quatsFwd, quatsBwd, self.smoothAlpha)

        pitchArr = np.zeros(n)
        rollArr = np.zeros(n)
        yawArr = np.zeros(n)

        quatsXyzw = np.column_stack([
            quatsSmooth[:, 1], quatsSmooth[:, 2],
            quatsSmooth[:, 3], quatsSmooth[:, 0]
        ])
        bodyRots = Rotation.from_quat(quatsXyzw)
        correctedRots = self.mountRot * bodyRots
        eulers = correctedRots.as_euler('xyz', degrees=True)
        rollArr = eulers[:, 0]
        pitchArr = eulers[:, 1]
        yawArr = eulers[:, 2]

        worldAccZ = self._rotateToWorldBatch(quatsSmooth, accelData)
        linAccZ = (worldAccZ - self.GRAVITY) * self.heaveGain
        heaveArr = self._computeHeave(linAccZ)

        return pitchArr, rollArr, yawArr, heaveArr

    def _computeHeave(self, linAccZ):
        n = len(linAccZ)
        if n < 10 or self.hpCutoff <= 0:
            vel = np.cumsum(linAccZ) * self.dt
            pos = np.cumsum(vel) * self.dt
            return pos

        fs = 1.0 / self.dt
        nyq = fs / 2.0
        cutoff = min(self.hpCutoff, nyq * 0.95)
        order = max(1, min(self.hpOrder, 4))

        try:
            b, a = butter(order, cutoff / nyq, btype='high')
        except ValueError:
            return np.cumsum(np.cumsum(linAccZ) * self.dt) * self.dt

        accFilt = filtfilt(b, a, linAccZ)
        vel = np.cumsum(accFilt) * self.dt

        try:
            velFilt = filtfilt(b, a, vel)
        except ValueError:
            velFilt = vel

        pos = np.cumsum(velFilt) * self.dt

        try:
            posFilt = filtfilt(b, a, pos)
        except ValueError:
            posFilt = pos

        return posFilt