#ifndef IMU_TO_DXL_DXL2_SLAVE_H
#define IMU_TO_DXL_DXL2_SLAVE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DXL2_BROADCAST_ID 0xFEu
#define DXL2_INST_STATUS 0x55u
#define DXL2_INST_SYNC_READ 0x82u

#define IMU_TO_DXL_ID 200u
#define IMU_TO_DXL_READ_ADDRESS 124u
#define IMU_TO_DXL_READ_LENGTH 12u

#define DXL2_MAX_PACKET_SIZE 256u

typedef enum {
  DXL2_PARSE_OK = 0,
  DXL2_PARSE_TOO_SHORT,
  DXL2_PARSE_BAD_HEADER,
  DXL2_PARSE_BAD_LENGTH,
  DXL2_PARSE_BAD_CRC,
  DXL2_PARSE_NOT_SYNC_READ,
  DXL2_PARSE_ID_NOT_REQUESTED,
  DXL2_PARSE_UNSUPPORTED_RANGE,
  DXL2_PARSE_STUFFING_OVERFLOW,
} dxl2_parse_result_t;

typedef struct {
  uint16_t address;
  uint16_t data_length;
  uint8_t slot_index;
  uint8_t slot_count;
} dxl2_sync_read_request_t;

uint16_t dxl2_crc_update(uint16_t crc, const uint8_t *data, size_t length);

dxl2_parse_result_t dxl2_parse_sync_read(
    const uint8_t *packet,
    size_t packet_length,
    uint8_t self_id,
    dxl2_sync_read_request_t *request);

size_t dxl2_build_status_packet(
    uint8_t id,
    uint8_t error,
    const uint8_t *data,
    size_t data_length,
    uint8_t *output,
    size_t output_capacity);

uint32_t dxl2_sync_read_slot_delay_us(
    const dxl2_sync_read_request_t *request,
    uint32_t baud_rate,
    uint32_t inter_packet_guard_us);

#endif
