#ifndef VEMINS_MEMORY_READER_H
#define VEMINS_MEMORY_READER_H

#include "engine_schema.h"
#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>
#include <sys/types.h>

#ifdef __cplusplus
extern "C" {
#endif

// Reader lifecycle & configuration
void memory_reader_init(void);
void memory_reader_release(void);
bool memory_reader_set_fd(int fd, int pid);
bool memory_reader_is_attached(void);

// Liveness & ELF validation
bool memory_reader_check_liveness(void);
bool memory_reader_validate_elf_magic(uint64_t base_addr);

// Core perception capture tick (Sub-1.0ms DMA)
int memory_reader_poll_frame(FrameSnapshotBinary *out_snapshot);

// Diagnostics & statistics
void memory_reader_get_stats(float *out_fps, float *out_latency_ms,
                             int *out_heroes, int *out_soldiers, int *out_monsters);

#ifdef __cplusplus
}
#endif

#endif // VEMINS_MEMORY_READER_H
