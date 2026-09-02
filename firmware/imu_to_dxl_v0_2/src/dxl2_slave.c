#include "dxl2_slave.h"

#include <string.h>

static bool is_header(const uint8_t *packet) {
  return packet[0] == 0xFFu && packet[1] == 0xFFu &&
         packet[2] == 0xFDu && packet[3] == 0x00u;
}

uint16_t dxl2_crc_update(uint16_t crc, const uint8_t *data, size_t length) {
  if (data == NULL && length != 0u) {
    return crc;
  }

  for (size_t index = 0; index < length; ++index) {
    crc ^= (uint16_t)data[index] << 8;
    for (uint8_t bit = 0; bit < 8u; ++bit) {
      crc = (crc & 0x8000u) != 0u
                ? (uint16_t)((crc << 1) ^ 0x8005u)
                : (uint16_t)(crc << 1);
    }
  }
  return crc;
}

static dxl2_parse_result_t unstuff_payload(
    const uint8_t *input,
    size_t input_length,
    uint8_t *output,
    size_t output_capacity,
    size_t *output_length) {
  size_t source = 0u;
  size_t destination = 0u;

  while (source < input_length) {
    if (destination >= output_capacity) {
      return DXL2_PARSE_STUFFING_OVERFLOW;
    }
    output[destination++] = input[source++];

    if (destination >= 3u && output[destination - 3u] == 0xFFu &&
        output[destination - 2u] == 0xFFu &&
        output[destination - 1u] == 0xFDu && source < input_length &&
        input[source] == 0xFDu) {
      ++source;
    }
  }

  *output_length = destination;
  return DXL2_PARSE_OK;
}

dxl2_parse_result_t dxl2_parse_sync_read(
    const uint8_t *packet,
    size_t packet_length,
    uint8_t self_id,
    dxl2_sync_read_request_t *request) {
  uint8_t payload[DXL2_MAX_PACKET_SIZE];
  size_t payload_length = 0u;

  if (packet == NULL || request == NULL || packet_length < 15u) {
    return DXL2_PARSE_TOO_SHORT;
  }
  if (!is_header(packet)) {
    return DXL2_PARSE_BAD_HEADER;
  }

  const uint16_t encoded_length =
      (uint16_t)packet[5] | ((uint16_t)packet[6] << 8);
  if ((size_t)encoded_length + 7u != packet_length || encoded_length < 8u) {
    return DXL2_PARSE_BAD_LENGTH;
  }

  const uint16_t expected_crc =
      (uint16_t)packet[packet_length - 2u] |
      ((uint16_t)packet[packet_length - 1u] << 8);
  if (dxl2_crc_update(0u, packet, packet_length - 2u) != expected_crc) {
    return DXL2_PARSE_BAD_CRC;
  }
  if (packet[4] != DXL2_BROADCAST_ID) {
    return DXL2_PARSE_NOT_SYNC_READ;
  }

  const dxl2_parse_result_t unstuff_result = unstuff_payload(
      &packet[7], packet_length - 9u, payload, sizeof(payload), &payload_length);
  if (unstuff_result != DXL2_PARSE_OK) {
    return unstuff_result;
  }
  if (payload_length < 6u || payload[0] != DXL2_INST_SYNC_READ) {
    return DXL2_PARSE_NOT_SYNC_READ;
  }

  request->address = (uint16_t)payload[1] | ((uint16_t)payload[2] << 8);
  request->data_length =
      (uint16_t)payload[3] | ((uint16_t)payload[4] << 8);

  const size_t id_count = payload_length - 5u;
  if (id_count > UINT8_MAX) {
    return DXL2_PARSE_BAD_LENGTH;
  }
  request->slot_count = (uint8_t)id_count;

  bool found = false;
  for (size_t index = 0u; index < id_count; ++index) {
    if (payload[5u + index] == self_id) {
      request->slot_index = (uint8_t)index;
      found = true;
      break;
    }
  }
  if (!found) {
    return DXL2_PARSE_ID_NOT_REQUESTED;
  }
  if (request->address != IMU_TO_DXL_READ_ADDRESS ||
      request->data_length != IMU_TO_DXL_READ_LENGTH) {
    return DXL2_PARSE_UNSUPPORTED_RANGE;
  }
  return DXL2_PARSE_OK;
}

static bool append_stuffed(
    uint8_t byte,
    uint8_t *output,
    size_t output_capacity,
    size_t *position) {
  if (*position >= output_capacity) {
    return false;
  }
  output[(*position)++] = byte;

  if (*position >= 3u && output[*position - 3u] == 0xFFu &&
      output[*position - 2u] == 0xFFu &&
      output[*position - 1u] == 0xFDu) {
    if (*position >= output_capacity) {
      return false;
    }
    output[(*position)++] = 0xFDu;
  }
  return true;
}

size_t dxl2_build_status_packet(
    uint8_t id,
    uint8_t error,
    const uint8_t *data,
    size_t data_length,
    uint8_t *output,
    size_t output_capacity) {
  if (output == NULL || (data == NULL && data_length != 0u) ||
      output_capacity < 11u) {
    return 0u;
  }

  const uint8_t header[5] = {0xFFu, 0xFFu, 0xFDu, 0x00u, id};
  memcpy(output, header, sizeof(header));
  size_t position = 7u;

  if (!append_stuffed(DXL2_INST_STATUS, output, output_capacity, &position) ||
      !append_stuffed(error, output, output_capacity, &position)) {
    return 0u;
  }
  for (size_t index = 0u; index < data_length; ++index) {
    if (!append_stuffed(data[index], output, output_capacity, &position)) {
      return 0u;
    }
  }

  const size_t stuffed_body_length = position - 7u;
  const size_t encoded_length = stuffed_body_length + 2u;
  if (encoded_length > UINT16_MAX || position + 2u > output_capacity) {
    return 0u;
  }
  output[5] = (uint8_t)(encoded_length & 0xFFu);
  output[6] = (uint8_t)(encoded_length >> 8);

  const uint16_t crc = dxl2_crc_update(0u, output, position);
  output[position++] = (uint8_t)(crc & 0xFFu);
  output[position++] = (uint8_t)(crc >> 8);
  return position;
}

uint32_t dxl2_sync_read_slot_delay_us(
    const dxl2_sync_read_request_t *request,
    uint32_t baud_rate,
    uint32_t inter_packet_guard_us) {
  if (request == NULL || baud_rate == 0u || request->slot_index == 0u) {
    return 0u;
  }

  const uint32_t status_bytes = 11u + request->data_length;
  const uint64_t packet_time_us =
      ((uint64_t)status_bytes * 10u * 1000000u + baud_rate - 1u) / baud_rate;
  return (uint32_t)((uint64_t)request->slot_index *
                    (packet_time_us + inter_packet_guard_us));
}
