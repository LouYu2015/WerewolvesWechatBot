'''
Copied from http://stackoverflow.com/a/17657304/4398908

Play a wave sound file.
'''
import pyaudio  
import wave

audioPath = None # Path to audio files

def playSound(name):
    #define stream chunk   
    chunk = 1024  

    #open a wav format music  
    f = wave.open('%s%s.wav' % (audioPath, name),"rb")
    #instantiate PyAudio  
    p = pyaudio.PyAudio()  
    #open stream  
    stream = p.open(format = p.get_format_from_width(f.getsampwidth()),  
                    channels = f.getnchannels(),  
                    rate = f.getframerate(),  
                    output = True)  
    #read data  
    data = f.readframes(chunk)  

    #play stream  
    while data:  
        stream.write(data)  
        data = f.readframes(chunk)  

    #stop stream  
    stream.stop_stream()  
    stream.close()  

    #close PyAudio  
    p.terminate()
