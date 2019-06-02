from google.cloud import texttospeech
import pygame
import time

tmp_tts_file = "temp_audio_%i.wav"
tmp_tts_file_id = 0

def tts_to_file(message, tts_client):
    global tmp_tts_file_id
    filename = tmp_tts_file % tmp_tts_file_id
    tmp_tts_file_id = (tmp_tts_file_id + 1) % 2

    # Set the text input to be synthesized
    synthesis_input = texttospeech.types.SynthesisInput(text=message)

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    voice = texttospeech.types.VoiceSelectionParams(
        language_code='nl-NL',
        name="nl-NL-Wavenet-A",
        ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

    # Select the type of audio file you want returned
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.LINEAR16,
        speaking_rate=0.80,
        pitch=-0.40)

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = tts_client.synthesize_speech(synthesis_input, voice, audio_config)

    # The response's audio_content is binary.
    with open(filename, "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)

    return filename

def play_sound_file(filename):

    if time.localtime().tm_hour >= 22 or time.localtime().tm_hour < 7:
        pygame.mixer.music.set_volume(0.1)
    else:
        pygame.mixer.music.set_volume(1)

    print(pygame.mixer.music.get_volume())

    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue

def tts_process(queue):
    # Init pygame audio mixer
    pygame.mixer.init(frequency=24000)

    # Instantiates a client
    tts_client = texttospeech.TextToSpeechClient()

    while True:
        alert = queue.get()

        # Alarm
        if "alert_type" in alert and alert["alert_type"]:
            tts_message = f"Prio {alert['priority']}. {alert['message']}"
            play_sound_file(f"{alert['alert_type']}.wav")
        elif alert["priority"]:
            tts_message = "Prio {}. {}".format(alert["priority"], alert["message"])
            play_sound_file(f"Prio_{alert['priority']}.wav")
        else:
            tts_message = alert["message"]
        print("{}: \"{}\"".format(alert["timestamp"], tts_message))

        # Text
        tts_filename = tts_to_file(tts_message, tts_client)
        play_sound_file(tts_filename)
        play_sound_file(tts_filename)
