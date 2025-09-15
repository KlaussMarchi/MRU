#ifndef TASKS_H
#define TASKS_H
#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include "../device/index.h"


class Tasks {
  private:
    TaskHandle_t Task;
    
  public:
    void handle() {
        //(function, name, size, NULL, priority, taskPointer, core)
        xTaskCreatePinnedToCore(setupTask, "Task", 5*1024, NULL, 1, &Task, 1);
        
        while(true)
            thread0();
    }
    
    static void setupTask(void* parameters){
        Serial.println("Thread 1 Started");

        while(true)
            thread1();
    }

    static void thread0(){
        device.sensors.handle();
    }

    static void thread1(){
        device.telemetry.handle();
    }
};


inline Tasks tasks;
#endif