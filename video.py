import os
from google.cloud import speech_v1p1beta1 as speech
from gtts import gTTS
import subprocess

# Set environment variable for authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "JSON.json"

def split_text(text, max_length=200):
    words = text.split()
    chunks = []
    chunk = []
    for word in words:
        if len(' '.join(chunk + [word])) <= max_length:
            chunk.append(word)
        else:
            chunks.append(' '.join(chunk))
            chunk = [word]
    if chunk:
        chunks.append(' '.join(chunk))
    return chunks

def generate_audio(text_chunks, sample_rate=16000):
    audio_files = []
    for i, chunk in enumerate(text_chunks):
        tts = gTTS(chunk)
        audio_file = f"audio_chunk{i+1}.mp3"
        tts.save(audio_file)
        # Convert to WAV with the correct sample rate
        wav_file = audio_file.replace('.mp3', '.wav')
        subprocess.run(['ffmpeg', '-i', audio_file, '-ar', str(sample_rate), wav_file])
        audio_files.append(wav_file)
    return audio_files

def transcribe_with_word_timestamps(audio_path, sample_rate=16000):
    client = speech.SpeechClient()
    with open(audio_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate,
        language_code="en-US",
        enable_word_time_offsets=True
    )

    response = client.recognize(config=config, audio=audio)
    words = []
    for result in response.results:
        alternative = result.alternatives[0]
        for word_info in alternative.words:
            word = word_info.word
            start_time = word_info.start_time.total_seconds()
            end_time = word_info.end_time.total_seconds()
            words.append((word, start_time, end_time))
            print(f"Word: {word}, Start: {start_time}, End: {end_time}")

    return words

def generate_srt(words, srt_path):
    with open(srt_path, "w") as srt_file:
        for i, (word, start, end) in enumerate(words):
            srt_file.write(f"{i+1}\n")
            srt_file.write(f"{format_time(start)} --> {format_time(end)}\n")
            srt_file.write(f"{word}\n\n")
    print(f"SRT file generated at {srt_path}")

def format_time(seconds):
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{int(seconds // 3600):02}:{int((seconds % 3600) // 60):02}:{int(seconds % 60):02},{milliseconds:03}"

def main():
    long_text = "Your long story text here..."
    text_chunks = split_text(long_text)
    sample_rate = 16000
    audio_files = generate_audio(text_chunks, sample_rate)

    all_words = []
    for audio_file in audio_files:
        words = transcribe_with_word_timestamps(audio_file, sample_rate)
        all_words.extend(words)

    srt_path = "output.srt"
    generate_srt(all_words, srt_path)

    # FFmpeg command to combine video, replace audio, and add subtitles
    video_path = "background.mp4"
    output_path = "output_video.mp4"
    audio_file = audio_files[0]
    ffmpeg_command = f'ffmpeg -i "{video_path}" -i "{audio_file}" -c:v libx264 -vf subtitles="{srt_path}" -map 0:v -map 1:a -shortest "{output_path}"'
    subprocess.run(ffmpeg_command, shell=True)
    
    print("Video creation completed!")

if __name__ == "__main__":
    main()
