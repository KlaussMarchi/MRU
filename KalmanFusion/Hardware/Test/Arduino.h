#ifndef ARDUINO_SHIM_H
#define ARDUINO_SHIM_H
#include <cmath>
#include <string>


// SO O QUE O KalmanModel USA DO ARDUINO, PARA COMPILAR O MODELO NO COMPUTADOR
class String : public std::string{
  public:
	String(const char* text): std::string(text){}
};

#endif
