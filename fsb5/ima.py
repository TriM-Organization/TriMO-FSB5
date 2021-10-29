#!/usr/bin/env python3
# -*- coding: utf-8

# typedef struct {
# 	char ckID [4];
# uint32_t ckSize;
# char formType [4];
# } RiffChunkHeader;
#
# typedef struct {
# 	char ckID [4];
# uint32_t ckSize;
# } ChunkHeader;
#
# #define ChunkHeaderFormat "4L"
#
# typedef struct {
# 	uint16_t FormatTag, NumChannels;
# uint32_t SampleRate, BytesPerSecond;
# uint16_t BlockAlign, BitsPerSample;
# uint16_t cbSize;
# union {
# 	uint16_t ValidBitsPerSample;
# uint16_t SamplesPerBlock;
# uint16_t Reserved;
# } Samples;
# int32_t ChannelMask;
# uint16_t SubFormat;
# char GUID [14];
# } WaveHeader;
#
# #define WaveHeaderFormat "SSLLSSSSLS"
#
# typedef struct {
# 	char ckID [4];
# uint32_t ckSize;
# uint32_t TotalSamples;
# } FactHeader;
#
# #define FactHeaderFormat "4LL"
#
# #define WAVE_FORMAT_IMA_ADPCM   0x11


def rebuild(sample):
	block_size = 72
	# block_size = 256 * sample.channels
	# if sample.frequency >= 11000:
	# 	block_size *= sample.frequency // 11000
	# samples_per_block = 505 																		# default factor
	# samples_per_block = (block_size - sample.channels * 4) * (sample.channels ^ 3) + 1			# Intel ADCPM factor
	# samples_per_block = (((block_size - (7 * sample.channels)) * 8) / (4 * sample.channels)) + 2	# MS ADCPM factor
	samples_per_block = (sample.samples // block_size + sample.samples % block_size) // sample.channels
	ret = bytearray()
	# ChunkID
	ret.extend(b"RIFF")
	# ChunkSize
	ret.extend(le(52 + len(sample.data), False))
	# Format
	ret.extend(b"WAVE")
	# Subchunk1ID
	ret.extend(b"fmt ")
	# Subchunk1Size
	ret.extend(le(20, False))
	# AudioFormat
	ret.extend(le(0x11, True))
	# NumChannels
	ret.extend(le(sample.channels, True))
	# SampleRate
	ret.extend(le(sample.frequency, False))
	# ByteRate <<
	# ret.extend(le((sample.frequency * block_size) // samples_per_block, False))
	ret.extend(le((sample.frequency * 10) // (sample.channels * 4), False))
	# BlockAlign <<
	ret.extend(le(block_size, True))
	# BitsPerSample
	ret.extend(le(4, True))
	# ByteExtraData
	ret.extend(le(2, True))
	# SamplesPerBlock <<
	ret.extend(le(samples_per_block, True))
	# FactHDR
	ret.extend(b"fact")
	# SubChunk2Size
	ret.extend(le(4, False))
	# TotalSamples
	ret.extend(le(sample.samples, False))
	# Subchunk3ID
	ret.extend(b"data")
	# Subchunk3Size
	ret.extend(le(len(sample.data), False))

	ret.extend(sample.data)

	return ret


def le(v: int, short: bool) -> bytearray:
	out = bytearray()
	out.append(v & 0xFF)
	out.append((v >> 8) & 0xFF)
	if not short:
		out.append((v >> 16) & 0xFF)
		out.append((v >> 24) & 0xFF)
	return out
