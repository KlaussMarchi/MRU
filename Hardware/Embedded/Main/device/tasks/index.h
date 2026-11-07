#ifndef TASKS_H
#define TASKS_H
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>


template <typename Parent> class Tasks {
  private:
	TaskHandle_t Task;
	Parent* device;

  public:
	Tasks(Parent* dev): 
		device(dev){}

	void handle(){
		if(!device->multitask){
			thread0();
			thread1();
			return;
		}

		//(function, name, size, NULL, priority, taskPointer, core)
		xTaskCreatePinnedToCore(setupTask, "Task", 8*1024, this, 1, &Task, 1);
		Serial.println("\nThread 1 Started");

		while(true)
			thread0();
	}

	static void setupTask(void* parameters) {
		auto taskInstance = static_cast<Tasks<Parent>*>(parameters);
		Serial.println("Thread 2 Started");

		while(true)
			taskInstance->thread1();
	}

	void thread0() {
		if(device->updater.active){    // A FLASH ESTA SENDO ESCRITA: SO OS LEDS ANDAM, PARA A thread1 RECEBER SEM DISPUTAR O NUCLEO
			device->components.handle();
			delay(5);
			return;
		}

		device->sensors.handle();
		device->processing.handle();
		device->components.handle();
		device->health.handle();
		device->updater.handle();
	}

	void thread1() { 
		device->telemetry.handle();
	}
};

#endif