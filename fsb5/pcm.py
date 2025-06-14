import wave
import struct
from io import BytesIO


def rebuild(sample, width):
    data = sample.data[: sample.samples * sample.channels * width]
    ret = BytesIO()
    with wave.open(ret, "wb") as wav:
        wav.setparams((sample.channels, width, sample.frequency, 0, "NONE", "NONE"))
        wav.writeframes(data)
    return ret.getvalue()


def rebuild_float(sample, width):
    data = sample.data[: sample.samples * width]
    ret = BytesIO()
    with PCMFloatWave_write(ret) as wav:
        wav.setparams((sample.channels, width, sample.frequency, 0, "NONE", "NONE"))
        wav.writeframes(data)
    return ret.getvalue()


fadpcm_coefs = (
    (0, 0),
    (60, 0),
    (122, 60),
    (115, 52),
    (98, 55),
    (0, 0),
    (0, 0),
    (0, 0),
)


def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)


def overflow(value, min_value, max_value):
    if min_value < value < max_value:
        return value
    else:
        return (value - min_value) % (2 * (max_value + 1)) + min_value
    # return (value - max_value + min_value) if value > max_value else ((value + max_value - min_value) if value < min_value else value)


def rebuild_pcm_data(sample_bytes):
    # header_length = 0xc
    # bytes_per_frame = 0x8c
    # samples_per_frame = (bytes_per_frame - header_length) * 2  # 256

    # num_frames = len(sample_bytes) // bytes_per_frame

    end_pos = len(sample_bytes) * 256 // 140

    pcm_data = b""

    stream = BytesIO(sample_bytes)

    out_pos = 0
    while out_pos < end_pos:
        # Read header
        coefs_bytes = stream.read(4)
        shifts_bytes = stream.read(4)
        hist1 = int.from_bytes(stream.read(2), "little", signed=True)
        hist2 = int.from_bytes(stream.read(2), "little", signed=True)

        coefs = int.from_bytes(coefs_bytes, "little")
        shifts = int.from_bytes(shifts_bytes, "little")

        for i in range(8):
            index = ((coefs >> i * 4) & 0x0F) % 0x07
            shift = (shifts >> i * 4) & 0x0F
            coef1 = fadpcm_coefs[index][0]
            coef2 = fadpcm_coefs[index][1]

            shift = 22 - shift

            for j in range(4):
                nibbles_bytes = stream.read(4)
                if len(nibbles_bytes) < 4:
                    raise ValueError("Unexpected end of data in nibbles read")
                nibbles = overflow(
                    int.from_bytes(nibbles_bytes, "little"), 0, 0xFFFFFFFF
                )

                for k in range(8):
                    sample = overflow(
                        overflow(nibbles >> (k * 4), -2147483648, 2147483647) & 0x0F,
                        -2147483648,
                        2147483647,
                    )
                    sample = overflow(
                        overflow(sample << 28, -2147483648, 2147483647) >> shift,
                        -2147483648,
                        2147483647,
                    )
                    sample = overflow(
                        overflow(
                            overflow(sample - hist2 * coef2, -2147483648, 2147483647)
                            + hist1 * coef1,
                            -2147483648,
                            2147483647,
                        )
                        >> 6,
                        -2147483648,
                        2147483647,
                    )
                    sample = clamp(sample, -32768, 32767)

                    pcm_data += sample.to_bytes(2, "little", signed=True)
                    out_pos += 1

                    hist2 = hist1
                    hist1 = sample

    return pcm_data


def rebuild_fadpcm(sample, width):

    data = sample.data[: sample.samples * sample.channels * width]

    pcm_shorts = rebuild_pcm_data(data)

    ret = BytesIO()

    with wave.open(ret, "wb") as wav_file:
        wav_file.setparams(
            (sample.channels, width, sample.frequency, 0, "NONE", "NONE")
        )

        # 写入 PCM 数据
        # wav_file.writeframesraw(pcm_shorts)
        wav_file.writeframes(pcm_shorts)

    return ret.getvalue()


WAVE_FORMAT_IEEE_FLOAT = 3


# 类型检查器会在下面这个类里报一堆 _file、_nchannels、_sampwidth 未定义的错误，但是不影响使用
# type checker might report errors here below, but it doesn't affect usage


class PCMFloatWave_write(wave.Wave_write):
    def _write_header(self, initlength):
        assert not self._headerwritten
        self._file.write(b"RIFF")
        if not self._nframes:
            self._nframes = initlength // (self._nchannels * self._sampwidth)
        self._datalength = self._nframes * self._nchannels * self._sampwidth
        try:
            self._form_length_pos = self._file.tell()
        except (AttributeError, OSError):
            self._form_length_pos = None
        self._file.write(
            struct.pack(
                "<L4s4sLHHLLHH4s",
                36 + self._datalength,
                b"WAVE",
                b"fmt ",
                16,
                WAVE_FORMAT_IEEE_FLOAT,
                self._nchannels,
                self._framerate,
                self._nchannels * self._framerate * self._sampwidth,
                self._nchannels * self._sampwidth,
                self._sampwidth * 8,
                b"data",
            )
        )
        if self._form_length_pos is not None:
            self._data_length_pos = self._file.tell()
        self._file.write(struct.pack("<L", self._datalength))
        self._headerwritten = True
