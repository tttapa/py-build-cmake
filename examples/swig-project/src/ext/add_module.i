%module add_module

%{
#include <cstdint>
%}

%include "stdint.i"

%rename(__version__) version;

%inline %{
extern int32_t add(int32_t a, int32_t b);
extern const char *const version;
%}
