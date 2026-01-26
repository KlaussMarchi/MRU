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
        xTaskCreatePinnedToCore(setupTask, "Task", 5*1024, this, 1, &Task, 1);
        Serial.println("Thread 1 Started");
        
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
        device->sensors.handle();
        device->leds.handle();
    }

    void thread1() { 
        device->telemetry.handle();
    }
};

#endif