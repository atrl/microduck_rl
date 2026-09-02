cmake_minimum_required(VERSION 3.16)
project(imu_to_dxl_protocol_core C)

add_library(dxl2_slave_core STATIC src/dxl2_slave.c)
target_include_directories(dxl2_slave_core PUBLIC include)
target_compile_features(dxl2_slave_core PUBLIC c_std_11)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(dxl2_slave_core PRIVATE -Wall -Wextra -Werror -pedantic)
endif()

enable_testing()
add_executable(test_dxl2_slave tests/test_dxl2_slave.c)
target_link_libraries(test_dxl2_slave PRIVATE dxl2_slave_core)
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
  target_compile_options(test_dxl2_slave PRIVATE -Wall -Wextra -Werror -pedantic)
endif()
add_test(NAME dxl2_slave_core COMMAND test_dxl2_slave)
