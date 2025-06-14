from collections import namedtuple
from enum import IntEnum
from io import BytesIO

from .utils import BinaryReader


__version__ = "0.1.0"
__author__ = ("Simon Pinfold", "Eilles W")


class SoundFormat(IntEnum):
    """
    FSB5 内部音频格式枚举类
    FSB5 inside audio format enum
    """

    NONE = 0
    PCM8 = 1
    PCM16 = 2
    PCM24 = 3
    PCM32 = 4
    PCMFLOAT = 5
    GCADPCM = 6
    IMAADPCM = 7
    VAG = 8
    HEVAG = 9
    XMA = 10
    MPEG = 11
    CELT = 12
    AT9 = 13
    XWMA = 14
    VORBIS = 15
    FADPCM = 16

    @property
    def file_extension(self):
        if self == SoundFormat.MPEG:
            return "mp3"
        elif self == SoundFormat.VORBIS:
            return "ogg"
        elif self.is_pcm:
            return "wav"
        elif (
            self.IMAADPCM
        ):  # 其实这也是一种波形类型 Actually this is also a kind of wave type
            return "acm"
        return "bin"

    @property
    def is_pcm(self):
        return self in (
            SoundFormat.PCM8,
            SoundFormat.PCM16,
            SoundFormat.PCM32,
            SoundFormat.PCMFLOAT,
            SoundFormat.FADPCM,
        )


FSB5Header = namedtuple(
    "FSB5Header",
    [
        "id",
        "version",
        "numSamples",
        "sampleHeadersSize",
        "nameTableSize",
        "dataSize",
        "mode",
        "zero",
        "hash",
        "dummy",
        "unknown",
        "size",
    ],
)
"""
FSB5 标头序列
FSB5 header names structure
"""

Sample = namedtuple(
    "Sample",
    [
        "name",
        "frequency",
        "channels",
        "dataOffset",
        "samples",
        "metadata",
        "dataEnd",
        "data",
    ],
)
"""
采样信息数据结构
Sample information data structure
"""

frequency_values = {
    1: 8000,
    2: 11000,
    3: 11025,
    4: 16000,
    5: 22050,
    6: 24000,
    7: 32000,
    8: 44100,
    9: 48000,
}
"""
可用的 元信息频率下标-频率 数值对应表
Available metadata_frequency_index-frequency value
"""


class MetadataChunkType(IntEnum):
    CHANNELS = 1
    FREQUENCY = 2
    LOOP = 3
    XMASEEK = 6
    DSPCOEFF = 7
    XWMADATA = 10
    VORBISDATA = 11


chunk_data_format = {
    MetadataChunkType.CHANNELS: "B",
    MetadataChunkType.FREQUENCY: "I",
    MetadataChunkType.LOOP: "II",
}

VorbisData = namedtuple("VorbisData", ["crc32", "unknown"])


def bits(val, start, len):
    """
    很重要的一个应该是用于定位的函数，但我没看懂
    A important function maybe for locating something but I didn't understand it
    """
    stop = start + len
    r = val & ((1 << stop) - 1)
    return r >> start


class FSB5:
    def __init__(self, stream, prefix=""):
        buf = BinaryReader(stream, endian="<")

        chunk = 10240000
        fpos = 0
        while True:
            ff = buf.read(chunk)
            offset = ff.find(b"FSB5")
            if offset > 0:
                offset += fpos
                break
            if not ff:
                break
            fpos += chunk

        if offset < 0:
            buf.seek(0)
            raise ValueError("Expected magic header 'FSB5' but got %r" % (buf.read(4)))

        buf.seek(offset)
        self.header = buf.read_struct_into(FSB5Header, "4s I I I I I I 8s 16s 8s")
        if self.header.version == 0:
            self.header = self.header._replace(unknown=buf.read_type("I"))
        self.header = self.header._replace(
            mode=SoundFormat(self.header.mode), size=buf.tell()
        )

        self.raw_size = (
            self.header.size
            + self.header.sampleHeadersSize
            + self.header.nameTableSize
            + self.header.dataSize
        )

        self.samples = []
        for i in range(self.header.numSamples):
            raw = buf.read_type("Q")
            next_chunk = bits(raw, 0, 1)
            frequency = bits(raw, 1, 4)
            channels = bits(raw, 1 + 4, 1) + 1
            dataOffset = bits(raw, 1 + 4 + 1, 28) * 16
            samples = bits(raw, 1 + 4 + 1 + 28, 30)

            chunks = {}
            while next_chunk:
                raw = buf.read_type("I")
                next_chunk = bits(raw, 0, 1)
                chunk_size = bits(raw, 1, 24)
                chunk_type = bits(raw, 1 + 24, 7)

                try:
                    chunk_type = MetadataChunkType(chunk_type)
                except ValueError:
                    pass

                if chunk_type == MetadataChunkType.VORBISDATA:
                    chunk_data = VorbisData(
                        crc32=buf.read_type("I"), unknown=buf.read(chunk_size - 4)
                    )
                elif chunk_type in chunk_data_format:
                    fmt = chunk_data_format[chunk_type]
                    if buf.struct_calcsize(fmt) != chunk_size:
                        err = (
                            "Expected chunk %s of size %d, SampleHeader specified %d"
                            % (chunk_type, buf.struct_calcsize(fmt), chunk_size)
                        )
                        raise ValueError(err)
                    chunk_data = buf.read_struct(fmt)
                else:
                    chunk_data = buf.read(chunk_size)

                chunks[chunk_type] = chunk_data

            if MetadataChunkType.FREQUENCY in chunks:
                frequency = chunks[MetadataChunkType.FREQUENCY][0]
            elif frequency in frequency_values:
                frequency = frequency_values[frequency]
            else:
                raise ValueError(
                    "Frequency value %d is not valid and no FREQUENCY metadata chunk was provided"
                )

            self.samples.append(
                Sample(
                    name="%04d" % (i),
                    frequency=frequency,
                    channels=channels,
                    dataOffset=dataOffset,
                    samples=samples,
                    metadata=chunks,
                    dataEnd=None,
                    data=None,
                )
            )

        if self.header.nameTableSize:
            nametable_start = buf.tell()

            samplename_offsets = [
                buf.read_type("I") for _ in range(self.header.numSamples)
            ]

            self.sampleIndex = {}

            for i in range(self.header.numSamples):
                buf.seek(nametable_start + samplename_offsets[i])
                name = buf.read_string(maxlen=self.header.nameTableSize)
                self.samples[i] = self.samples[i]._replace(name=name.decode("utf-8"))

        buf.seek(
            self.header.size + self.header.sampleHeadersSize + self.header.nameTableSize
        )
        for i in range(self.header.numSamples):
            data_start = self.samples[i].dataOffset
            data_end = data_start + self.header.dataSize
            if i < self.header.numSamples - 1:
                data_end = self.samples[i + 1].dataOffset
            self.samples[i] = self.samples[i]._replace(dataEnd=data_end)

        self.sampleIndex = {}
        for s in self.samples:
            if not prefix or s.name.startswith(prefix):
                self.sampleIndex[s.name[len(prefix) :]] = s
        self.buf = buf

    def __getitem__(self, name):
        sample = self.sampleIndex[name]
        return self._rebuild_sample(sample)

    def __contains__(self, name):
        return name in self.sampleIndex

    def _rebuild_sample(self, sample):
        base = (
            self.header.size + self.header.sampleHeadersSize + self.header.nameTableSize
        )
        self.buf.seek(base + sample.dataOffset)
        sample = sample._replace(data=self.buf.read(sample.dataEnd - sample.dataOffset))
        if self.header.mode == SoundFormat.MPEG:
            return sample.data
        elif self.header.mode == SoundFormat.VORBIS:
            # import here as vorbis.py requires native libraries
            from .vorbis import rebuild

            return rebuild(sample)
        elif self.header.mode.is_pcm:
            from .pcm import rebuild, rebuild_float

            if self.header.mode == SoundFormat.PCM8:
                width = 1
            elif self.header.mode == SoundFormat.PCM16:
                width = 2
            elif self.header.mode == SoundFormat.PCMFLOAT:
                width = 4
                return rebuild_float(sample, width)
            else:
                width = 4
            return rebuild(sample, width)
        elif self.header.mode == SoundFormat.IMAADPCM:
            from .ima import rebuild

            return rebuild(sample)
        else:
            return sample.data

    # raise NotImplementedError("Decoding samples of type %s is not supported" % (self.header.mode))

    def get_sample_extension(self):
        return self.header.mode.file_extension


def load(data):
    return FSB5(data)
