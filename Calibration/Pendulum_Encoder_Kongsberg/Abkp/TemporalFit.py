class TemporalFit:
    def __init__(self, time, xData, yData, max_iter=2100000000):
        self.time  = np.array(time)
        self.xData = np.array(xData)
        self.yData = np.array(yData)
        self.max_iter = max_iter
        self.coefs = []

    def f(self, x, a, b):
        return a*x + b

    def apply(self, data):
        if len(self.coefs) == 0:
            return None

        return self.f(np.array(data), *self.coefs)
    
    def update(self):
        result      = curve_fit(self.f, self.xData, self.yData, maxfev=self.max_iter)
        self.coefs  = [float(round(coef, 12)) for coef in list(result[0])]
        self.yModel = self.apply(self.xData)
        
        self.error = (self.yData - self.yModel)
        self.rmse  = np.sqrt(np.mean(self.error**2))
        self.mae   = np.mean(np.abs(self.error))
        self.max_error = np.max(np.abs(self.error))

        self.scale_factor_error = np.abs(1.0 - self.coefs[0]) * 100 
        self.std_noise = self.error.std()
        
        ss_res = np.sum(self.error**2) 
        ss_tot = np.sum((self.yData - np.mean(self.yData))**2) 

        if ss_tot == 0:
            self.r2 = 1.0 if ss_res == 0 else 0.0
        else:
            self.r2 = 1 - float(ss_res / ss_tot)

    def plot(self, view_limits=(0, 1)):
        t_max = self.time[-1]
        
        mask = ((self.time >= t_max * view_limits[0]) & (self.time <= t_max * view_limits[1])) if view_limits else slice(None)
        t_plot   = self.time[mask]
        x_plot   = self.xData[mask]
        y_plot   = self.yData[mask]
        mod_plot = self.yModel[mask]
        err_plot = self.error[mask]
        title = f" (Zoom: {t_max * view_limits[0]:.1f}s a {t_max * view_limits[1]:.1f}s)" if view_limits else ""

        plt.figure(figsize=(20, 5))
        plt.subplot(1, 2, 1)
        plt.plot(t_plot, y_plot, color='blue', label='reference')
        plt.plot(t_plot, mod_plot, color='red', label='model')
        plt.xlabel('time'); plt.ylabel('response')
        plt.legend(); plt.title(f'R2 Score {self.r2:.3f}')
        plt.grid()

        plt.subplot(1, 2, 2)
        plt.plot(t_plot, err_plot, color='blue')
        plt.xlabel('time'); plt.ylabel('response')
        plt.ylim(-self.max_error*3, self.max_error*3)
        plt.title(f'temporal error (mean={self.mae:.3f})')
        plt.grid(); plt.show()

    def display(self):
        display(pd.DataFrame([{'r2': self.r2, 'mae': self.mae, 'rmse': self.rmse, 'max_error': self.max_error}]))