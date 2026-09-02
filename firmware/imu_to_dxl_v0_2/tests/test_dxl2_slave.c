#include "dxl2_slave.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static size_t make_sync_read(
    const uint8_t *ids,
    size_t id_count,
    uint16_t address,
    uint16_t data_length,
    uint8_t *packet,
    size_t capacity) {
  const size_t total = 14u + id_count;
  assert(capacity >= total);
  assert(id_count > 0u && id_count <= UINT8_MAX);

  packet[0] = 0xFFu;
  packet[1] = 0xFFu;
  packet[2] = 0xFDu;
  packet[3] = 0x00u;
  packet[4] = DXL2_BROADCAST_ID;
  const uint16_t encoded_length = (uint16_t)(7u + id_count);
  packet[5] = (uint8_t)(encoded_length & 0xFFu);
  packet[6] = (uint8_t)(encoded_length >> 8);
  packet[7] = DXL2_INST_SYNC_READ;
  packet[8] = (uint8_t)(address & 0xFFu);
  packet[9] = (uint8_t)(address >> 8);
  packet[10] = (uint8_t)(data_length & 0xFFu);
  packet[11] = (uint8_t)(data_length >> 8);
  memcpy(&packet[12], ids, id_count);
  const uint16_t crc = dxl2_crc_update(0u, packet, total - 2u);
  packet[total - 2u] = (uint8_t)(crc & 0xFFu);
  packet[total - 1u] = (uint8_t)(crc >> 8);
  return total;
}

static void test_official_ping_crc(void) {
  const uint8_t ping_without_crc[] = {
      0xFFu, 0xFFu, 0xFDu, 0x00u, 0x01u, 0x03u, 0x00u, 0x01u};
  assert(dxl2_crc_update(0u, ping_without_crc, sizeof(ping_without_crc)) ==
         0x4E19u);
}

static void test_sync_read_first_slot(void) {
  const uint8_t ids[] = {IMU_TO_DXL_ID, 10u, 11u, 12u};
  uint8_t packet[64];
  dxl2_sync_read_request_t request = {0};
  const size_t length = make_sync_read(
      ids,
      sizeof(ids),
      IMU_TO_DXL_READ_ADDRESS,
      IMU_TO_DXL_READ_LENGTH,
      packet,
      sizeof(packet));

  assert(dxl2_parse_sync_read(
             packet, length, IMU_TO_DXL_ID, &request) == DXL2_PARSE_OK);
  assert(request.address == IMU_TO_DXL_READ_ADDRESS);
  assert(request.data_length == IMU_TO_DXL_READ_LENGTH);
  assert(request.slot_index == 0u);
  assert(request.slot_count == 4u);
  assert(dxl2_sync_read_slot_delay_us(&request, 1000000u, 20u) == 0u);
}

static void test_sync_read_later_slot_delay(void) {
  const uint8_t ids[] = {10u, 11u, IMU_TO_DXL_ID};
  uint8_t packet[64];
  dxl2_sync_read_request_t request = {0};
  const size_t length = make_sync_read(
      ids,
      sizeof(ids),
      IMU_TO_DXL_READ_ADDRESS,
      IMU_TO_DXL_READ_LENGTH,
      packet,
      sizeof(packet));

  assert(dxl2_parse_sync_read(
             packet, length, IMU_TO_DXL_ID, &request) == DXL2_PARSE_OK);
  assert(request.slot_index == 2u);
  assert(dxl2_sync_read_slot_delay_us(&request, 1000000u, 20u) == 500u);
}

static void test_rejections(void) {
  const uint8_t ids[] = {IMU_TO_DXL_ID, 10u};
  uint8_t packet[64];
  dxl2_sync_read_request_t request = {0};
  size_t length = make_sync_read(
      ids, sizeof(ids), 123u, IMU_TO_DXL_READ_LENGTH, packet, sizeof(packet));
  assert(dxl2_parse_sync_read(
             packet, length, IMU_TO_DXL_ID, &request) ==
         DXL2_PARSE_UNSUPPORTED_RANGE);

  length = make_sync_read(
      ids,
      sizeof(ids),
      IMU_TO_DXL_READ_ADDRESS,
      IMU_TO_DXL_READ_LENGTH,
      packet,
      sizeof(packet));
  packet[length - 1u] ^= 0x01u;
  assert(dxl2_parse_sync_read(
             packet, length, IMU_TO_DXL_ID, &request) == DXL2_PARSE_BAD_CRC);

  const uint8_t other_ids[] = {10u, 11u};
  length = make_sync_read(
      other_ids,
      sizeof(other_ids),
      IMU_TO_DXL_READ_ADDRESS,
      IMU_TO_DXL_READ_LENGTH,
      packet,
      sizeof(packet));
  assert(dxl2_parse_sync_read(
             packet, length, IMU_TO_DXL_ID, &request) ==
         DXL2_PARSE_ID_NOT_REQUESTED);
}

static void test_status_packet_and_stuffing(void) {
  uint8_t output[64];
  const uint8_t ordinary[IMU_TO_DXL_READ_LENGTH] = {0};
  size_t length = dxl2_build_status_packet(
      IMU_TO_DXL_ID, 0u, ordinary, sizeof(ordinary), output, sizeof(output));
  assert(length == 23u);
  assert(output[4] == IMU_TO_DXL_ID);
  assert(output[5] == 16u && output[6] == 0u);
  const uint16_t crc = (uint16_t)output[length - 2u] |
                       ((uint16_t)output[length - 1u] << 8);
  assert(dxl2_crc_update(0u, output, length - 2u) == crc);

  const uint8_t needs_stuffing[] = {0xAAu, 0xFFu, 0xFFu, 0xFDu, 0xBBu};
  length = dxl2_build_status_packet(
      IMU_TO_DXL_ID,
      0u,
      needs_stuffing,
      sizeof(needs_stuffing),
      output,
      sizeof(output));
  const uint8_t stuffed[] = {0xFFu, 0xFFu, 0xFDu, 0xFDu};
  bool found = false;
  for (size_t index = 0u; index + sizeof(stuffed) <= length; ++index) {
    if (memcmp(&output[index], stuffed, sizeof(stuffed)) == 0) {
      found = true;
      break;
    }
  }
  assert(found);
  assert(output[5] == 10u && output[6] == 0u);
}

int main(void) {
  test_official_ping_crc();
  test_sync_read_first_slot();
  test_sync_read_later_slot_delay();
  test_rejections();
  test_status_packet_and_stuffing();
  puts("dxl2_slave_core: all tests passed");
  return 0;
}
