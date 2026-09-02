# `imu_to_dxl` v0.2 firmware core

This directory contains the host-testable, allocation-free protocol core for
the STM32G030C8T6 bench board. It closes the gap in ROBOTIS'
`Dynamixel2Arduino::Slave`, whose current instruction dispatcher handles Ping,
Read and Write but not broadcast Sync Read.

Implemented here:

- Dynamixel Protocol 2.0 CRC-16;
- packet length and CRC validation;
- byte unstuffing for incoming instructions;
- broadcast Sync Read (`0x82`) parsing;
- the fixed ID 200, address 124, 12-byte Microduck contract;
- response slot detection and conservative later-slot timing calculation;
- Status Packet (`0x55`) generation with byte stuffing and CRC.

Run the portable tests with the system C compiler:

```bash
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Ifirmware/imu_to_dxl_v0_2/include \
  firmware/imu_to_dxl_v0_2/src/dxl2_slave.c \
  firmware/imu_to_dxl_v0_2/tests/test_dxl2_slave.c \
  -o /tmp/test_dxl2_slave
/tmp/test_dxl2_slave
```

The same core also has an optional CMake build for embedded-toolchain reuse:

```bash
cmake -S firmware/imu_to_dxl_v0_2 -B /tmp/imu_to_dxl_v0_2_build
cmake --build /tmp/imu_to_dxl_v0_2_build
ctest --test-dir /tmp/imu_to_dxl_v0_2_build --output-on-failure
```

## STM32 integration contract

The PCB intentionally leaves PF0/PF1 unconnected. Configure USART1 automatic
baud-rate detection with `ABRMOD=00`, which measures the first start bit. A
Dynamixel packet begins with `0xFF`, so the board can derive BRR from the bus
master before replying instead of assuming that an untrimmed HSI16 frequency is
exact. Treat `ABRE` or a missing `ABRF` as a no-response fault; never transmit
using an unvalidated BRR.

The hardware adapter must:

1. keep `TX_ENABLE` low from reset;
2. receive a complete packet into a bounded DMA/ring buffer;
3. call `dxl2_parse_sync_read`; verify that the current Microduck runtime places
   ID200 in slot zero, or honor `dxl2_sync_read_slot_delay_us` before replying;
4. atomically copy the latest 12-byte IMU snapshot;
5. assert `TX_ENABLE`, transmit the generated Status Packet, wait for USART TC,
   then deassert `TX_ENABLE` immediately;
6. use the official ST LSM6DSV16X driver and sensor-fusion example for SPI,
   FIFO, gyro and SFLP configuration.

Still hardware-dependent and therefore not claimed complete here: STM32CubeG0
startup, DMA/IRQ glue, SPI/FIFO service, watchdog/fault handling and oscilloscope
validation. The PCB is an electrical prototype; it must pass the bring-up gates
before connection to the complete robot bus.

Primary references:

- <https://github.com/pollen-robotics/microduck/blob/main/duck-control/src/bus.rs>
- <https://github.com/ROBOTIS-GIT/emanual/blob/master/docs/en/dxl/protocol2.md>
- <https://github.com/ROBOTIS-GIT/Dynamixel2Arduino/blob/master/src/utility/slave.cpp>
- <https://www.st.com/resource/en/application_note/an4908-getting-started-with-usart-automatic-baud-rater-detection-for-stm32-mcus-stmicroelectronics.pdf>
- <https://github.com/STMicroelectronics/STMems_Standard_C_drivers/blob/master/lsm6dsv16x_STdC/examples/lsm6dsv16x_sensor_fusion.c>
