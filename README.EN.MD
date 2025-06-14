# TriMO-FSB5

Python library and tool to extract FSB5 (FMOD Sample Bank) files.

### Supported formats

* MPEG
* Vorbis (OGG)
* WAVE (PCM8, PCM16, PCM32, PCMFLOAT, FADPCM)

Other formats can be identified but will be extracted as `.dat` files and may not play as the headers may be missing.

## Tool Usage

```
usage: extract.py [-h] [-o OUTPUT_DIRECTORY] [-p] [-q]
                  [fsb_file [fsb_file ...]]

Extract audio samples from FSB5 files

positional arguments:
  fsb_file              FSB5 container to extract audio from (defaults to
                        stdin)

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        output directory to write extracted samples into
  -q, --quiet           suppress output of header and sample information
                        (samples that failed to decode will still be printed)
 ```

#### Resource files

Unity3D packs multiple FSB5 files each containing a single sample into it's `.resource` files.
python-fsb5 will automatically extract all samples if multiple FSB5s are found within one file.
Output files will be prefixed with the (0 based) index of their FSB container within the resource file e.g. `out/sounds-15-track1.wav` is the path for a WAVE sample named track1 which is contained within the 16th FSB file within sounds.resource.

#### Unnamed samples

FSB5 does not require samples to store a name. If samples are stored without a name they will use their index within the FSB e.g. `sounds-0000.mp3` is the first sample in sounds.fsb.

## Requirements

python-fsb5 should work with python3 from version 3.2 and up.

`libogg` and `libvorbis` are required to decode ogg samples. For linux simply install from your package manager. For windows ensure the dlls are avaliable (ie. in System32 or the directory you are running the script from). Known working dlls are avaliable as part of the [release](https://github.com/HearthSim/python-fsb5/releases/tag/b7bf605).

If ogg files are not required to be decoded then the libraries are not required.

## Library usage

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

#### Useful header properties

* `numSamples`: The number of samples contained in the file
* `mode`: The audio format of all samples. Available formats are: (The table reference from [C# SFB5 library](https://github.com/SamboyCoding/Fmod5Sharp))
| Format| Format in this Library | Supportance | Extension | Notes |
| :-----: | :-----:|:--------------: | :---------: | :----------: |
| NONE | `fsb5.SoundFormat.NONE` | ?? | ?? | |
| PCM8 | `fsb5.SoundFormat.PCM8` | ✔️ | wav | |
| PCM16 | `fsb5.SoundFormat.PCM16` | ✔️ | wav | |
| PCM24 | `fsb5.SoundFormat.PCM24` | ❌ | | No games have ever been observed in the wild using this format. |
| PCM32 | `fsb5.SoundFormat.PCM32` | ✔️ | wav | Supported in theory. No games have ever been observed in the wild using this format. |
| PCMFLOAT | `fsb5.SoundFormat.PCMFLOAT` | ❌ | | Seen in at least one JRPG. |
| GCADPCM | `fsb5.SoundFormat.GCADPCM` | ❌ | wav | Seen in Unity games. |
| IMAADPCM | `fsb5.SoundFormat.IMAADPCM` | ✔️ | acm | Seen in Unity games. |
| VAG | `fsb5.SoundFormat.VAG` | ❌ | | No games have ever been observed in the wild using this format. |
| HEVAG | `fsb5.SoundFormat.HEVAG` | ❌ | | Very rarely used - only example I know of is a game for the PS Vita. |
| XMA | `fsb5.SoundFormat.XMA` | ❌ | | Mostly used on Xbox 360. |
| MPEG | `fsb5.SoundFormat.MPEG` | ✔️ | mp3 | Used in some older games. |
| CELT | `fsb5.SoundFormat.CELT` | ❌ | | Used in some older indie games. |
| AT9 | `fsb5.SoundFormat.AT9` | ❌ | | Native format for PlayStation Audio, including in Unity games. | 
| XWMA | `fsb5.SoundFormat.XWMA` | ❌ | | No games have ever been observed in the wild using this format. |
| VORBIS | `fsb5.SoundFormat.VORBIS` | ✔️ | ogg | Very commonly used in Unity games. |
| FADPCM | `fsb5.SoundFormat.FADPCM` | ✔️ | wav | Seen in Minecraft: Bedrock Edition |

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
