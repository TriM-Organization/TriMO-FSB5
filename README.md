# TriMO-FSB5

适用于 Python 的 FSB5 文件解析库及工具集。

Python library and tool to extract FSB5 (FMOD Sample Bank) files.

### 支持的格式

* [x] MPEG 格式
* [x] Vorbis (OGG)
* [x] 波形格式（PCM8, PCM16, PCM32, PCMFLOAT, FADPCM）

若存在其他格式，也许能解析，但会以 `.dat` 的文件后缀析出，且有可能因缺失文件标头而无法播放。

## 工具之用法

```
用法：

  extract.py [-h] [-o 输出目录] [-p] [-q] [fsb_file [fsb_file ...]]

从 FSB5 格式文件析出音频采样

位置参数：
  fsb_file              用以解析并提取的 FSB5 格式内容（默认从 stdin 读入）

可选参数：
  -h, --help            展示此帮助信息并退出
  -o 输出目录, --output-directory 输出目录
                        指定将采样文件提取到哪个目录
  -q, --quiet           不输出文件表头及采样信息
                        （若该采样无法正常解码，此消息仍会输出）
 ```

#### 对于音频资源集合文件的处理

类似 Unity3D 将多个 FSB5 文件组合成一个 `.resource` 文件，每个文件包含一个单独的采样的这种情况，我们称之为“音频资源集”的文件，其中包含多个 FSB5 格式信息。

而 TriMO-FSB5 可自动将该资源集合中的所有采样全部提取。

Output files will be prefixed with the (0 based) index of their FSB container within the resource file e.g. `out/sounds-15-track1.wav` is the path for a WAVE sample named track1 which is contained within the 16th FSB file within sounds.resource.

#### 对于无名音频采样的处理

FSB5 并不强制存储音频采样的名称，因此如果出现未命名的采样，解析并提取时会采用其在 FSB 文件中的索引。比如 `sounds-0000.mp3` 就是在 sounds.fsb 文件中的第一个音频采样。

## 需求及环境

原 python-fsb5 项目是期望运行于 Python 3.2 及以上版本的，虽然我们当前版本改动不大，
但是目前我们开发使用的版本是 3.10，我会尽量避免新特性使用，但实际标注会写需求为 3.8 及以上的 Python 版本。

若要解码 OGG 格式的采样，则需求 `libogg` 和 `libvorbis` 两库。在 Linux 环境下，只需要用包管理器安装即可。而在 Windows 系统下则需要确保 dll 文件是可被引用到的了（即其存在于 System32 或运行目录下）。已知可用的 dll 文件已经在原仓库的这个 [发布版本](https://github.com/HearthSim/python-fsb5/releases/tag/b7bf605) 中释出了。

但若不需要将 OGG 解码，则也就不需要这两个库。

## 库的调用方法

```python
import fsb5

# read the file into a FSB5 object
with open('sample.fsb', 'rb') as f:
  fsb = fsb5.FSB5(f.read())

print(fsb.header)

# get the extension of samples based off the sound format specified in the header
ext = fsb.get_sample_extension()

# iterate over samples
for sample in fsb.samples:
  # print sample properties
  print('''\t{sample.name}.{extension}:
  Frequency: {sample.frequency}
  Channels: {sample.channels}
  Samples: {sample.samples}'''.format(sample=sample, extension=ext))

  # rebuild the sample and save
  with open('{0}.{1}'.format(sample.name, ext), 'wb') as f:
    rebuilt_sample = fsb.rebuild_sample(sample)
    f.write(rebuilt_sample)
```

#### 有用的标头成分

* `numSamples`: 文件中包含的音频采样数量
* `mode`: 音频采样的编码格式，可用如下：（表格参考 [C# 的 SFB5 库](https://github.com/SamboyCoding/Fmod5Sharp)的内容简介）

| 格式| 库内格式 | 支持情况 | 拓展名 | 备注 |
| :-----: | :-----:|:--------------: | :---------: | :----------: |
| NONE | `fsb5.SoundFormat.NONE` | ?? | ?? | |
| PCM8 | `fsb5.SoundFormat.PCM8` | ✔️ | wav | |
| PCM16 | `fsb5.SoundFormat.PCM16` | ✔️ | wav | |
| PCM24 | `fsb5.SoundFormat.PCM24` | ❌ | | 未见使用此编码者 |
| PCM32 | `fsb5.SoundFormat.PCM32` | ✔️ | wav | 理论支持，但未见使用此编码者 |
| PCMFLOAT | `fsb5.SoundFormat.PCMFLOAT` | ❌ | | 在至少一个 日式角色扮演游戏 中瞧见过 |
| GCADPCM | `fsb5.SoundFormat.GCADPCM` | ❌ | wav | 在 Unity 游戏里瞧见过 |
| IMAADPCM | `fsb5.SoundFormat.IMAADPCM` | ✔️ | acm | 在 Unity 游戏里瞧见过 |
| VAG | `fsb5.SoundFormat.VAG` | ❌ | | 未见使用此编码者 |
| HEVAG | `fsb5.SoundFormat.HEVAG` | ❌ | | 极其稀有 - 惟一所知的是一个运行于 PS Vita 上的游戏 |
| XMA | `fsb5.SoundFormat.XMA` | ❌ | | 大多在 Xbox 360 上使用 |
| MPEG | `fsb5.SoundFormat.MPEG` | ✔️ | mp3 | 在一些老游戏中用的多 |
| CELT | `fsb5.SoundFormat.CELT` | ❌ | | 在一些老的独立游戏里用的多 |
| AT9 | `fsb5.SoundFormat.AT9` | ❌ | | PlayStation 音频的原生格式，其中也包括 Unity 游戏 | 
| XWMA | `fsb5.SoundFormat.XWMA` | ❌ | | 未见使用此编码者 |
| VORBIS | `fsb5.SoundFormat.VORBIS` | ✔️ | ogg | 在 Unity 游戏里使用极为频繁 |
| FADPCM | `fsb5.SoundFormat.FADPCM` | ✔️ | wav | Minecraft 基岩版的大量音效使用此种格式 |

#### Useful sample properties

* `name` : The name of the sample, or a 4 digit number if names are not provided.
* `frequency` : The sample rate of the audio
* `channels` : The number of channels of audio (either 1 or 2)
* `samples` : The number of samples in the audio
* `metadata` : A dictionary of `fsb5.MetadataChunkType` to tuple (sometimes namedtuple) or bytes.

All contents of sample.metadata is optional and often not provided. Several metadata types seem to override sample properties.

Supported `fsb5.MetadataChunkType` s are:
 * `CHANNELS` : A 1-tuple containing the number of channels
 * `FREQUENCY` : A 1-tuple containing the sample rate
 * `LOOP` : A 2-tuple of the loop start and end
 * `XMASEEK` : Raw bytes
 * `DSPCOEFF` : Raw bytes
 * `XWMADATA` : Raw bytes
 * `VORBISDATA` : A named tuple with properties `crc32` (int) and `unknown` (bytes)

If a metadata chunk is unrecognized it will be included in the dictionary as an interger mapping to a bytes.

#### Rebuilding samples

Samples also have the `data` property.
This contains the raw, unprocessed audio data for that sample from the FSB file.
To reconstruct a playable version of the audio use `rebuild_sample` on the FSB5 object passing the sample desired to be rebuilt.

## License

This software is a fork of the original python-fsb5 library by Simon Pinfold.  
And this fork is now licensed under the terms of the Apache 2.0 License.  
Original python-fsb5 is licensed under the terms of the MIT license.  

The full text of the license is available in the [LICENSE.md](./LICENSE.md) file.  
