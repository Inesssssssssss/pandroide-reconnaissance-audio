from faster_whisper import WhisperModel
from ollama import chat
import time
import collections
import re
import os
import glob
import matplotlib.pyplot as plt
import numpy as np

# All mentions of 'data' refer to : 
#     - execution time
#     - accuracy score
# transcript and transcription are interchangeable

# Audio processing stuff #

def getTranscript(audioPath, model_size, record):
    '''
    Fait la transcription du fichier audio donnée
    
    Args:
        audioPath : str - path to audio file (m4a or mp3)
        model_size : str - name of the model used to process the audio files
        record : bool - if True it writes the data into a file, else just prints it
    
    Returns:
        transcript : str - transcription of the audio
    
    '''

    # model_size = "large-v3"

    # Run on GPU with FP16
    # model = WhisperModel(model_size, device="cuda", compute_type="float16")

    # or run on GPU with INT8
    # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
    
    # or run on CPU with INT8
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    start = time.time()
    segments, info = model.transcribe(audioPath, beam_size=5)
    end1 = time.time()
    transcribe_t = end1 - start

    transcript = ""
    for segment in segments:
        # print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        transcript += segment.text

    end2 = time.time()
    total_t = end2 - start
    if record:
        directory = "data/" + model_size
        if not os.path.exists(directory):
            os.makedirs(directory)
        saveData(audioPath, model_size + "/exec_time", total_t)
        # to plot a comparison of exec time of func transcribe and the time with saving text
        file = open("data/" + model_size + "/comparison_exec_time.txt", "a")
        file.write("%.2f\t%.2f\n" % (transcribe_t, total_t))
        file.close()
    else :
        print("Transcription of audio '%s' took : %.2fs" % (getFileName(audioPath),total_t))
    
    transcript_dir = "transcriptions/" + model_size
    if not os.path.exists(transcript_dir):
        os.makedirs(transcript_dir)
    saveTranscript(transcript, transcript_dir + "/fw_"+ getFileName(audioPath) + ".txt")

    return transcript

def saveTranscript(transcript, filePath):
    '''
    Creates a file and saves the transcriptions of the audioPath done by faster-whisper
    as well as record the execution time into ecxec_time.txt file
    
    Args:
        transcript : str - content (stranscript) to save into a file
        filePath : str - file path to the file where the transcriptions will be saved
    '''

    file = open(filePath, "w")
    file.write(transcript)
    file.close()

def saveData(audioPath, dataType, data):
    '''
    Saves the data (execution time or score) into a file in the directory 'data'

    Args:
        audioPath : str - reference to know to wich audio file the data is from
        dataType : str - name of the file where the data is going to be saved
        data : float - the data to save
    '''
    try:
        file = open("data/" + dataType + ".txt", "a")
    except:
        file = open("data/" + dataType + ".txt", "w")
    file.write(getFileName(audioPath) + "\t%.2f\n" % (data))
    file.close()

def getScore(audioPath, og_file, model_size, record):
    '''
    Gives accuracy score to the transcription done by faster-wshiper out of 100.
    Score = num of words missing in fw_transcript (compared to og_text)/ total words in og_text
    
    Args:
        audioPath : str - path to audio file (m4a or mp3)
        og_file : str - file path to transcription
        model_size : str - name of the model used to process the audio files
        record : bool - if True it writes the data into a file, else just prints it
    
    Returns:
        score : float
    '''
    # Transcription faite par faster whisper
    fw_file = "transcriptions/" + model_size + "/fw_"+getFileName(audioPath)+".txt"
    fwFile = open(fw_file, "r")
    fw_read = fwFile.read()
    fwFile.close()

    # Transcription faites par nous utilisée comme référence
    if og_file==None:
        og_file = "transcriptions/original/og_"+getFileName(audioPath)+".txt"
    ogFile = open(og_file, "r")
    og_read = ogFile.read()
    ogFile.close()

    # On transforme le texte en liste de mots
    fw_text = list(filter(None, re.split(r"[,.?!\s\t\n]\s*", fw_read)))
    og_text = list(filter(None, re.split(r"[,.?!\s\t\n]\s*", og_read)))

    total_mots = len(og_text)

    # missedWords donne les mots qui ne sont pas dans fw_text par rapport à og_text
    missedWords = set(og_text) - set(fw_text)

    # Transforme la liste de mots og_text en dictionaire de fréquences de mots
    # pour savoir le nombre total de mots qui manquent (cas où un mots serait plusieurs fois
    # mal compris)
    og_dict = collections.Counter(og_text)
    cpt = 0 
    for word in missedWords:
        cpt += og_dict[word]
    
    score = ((total_mots - cpt)/total_mots)*100
    if record:
        saveData(audioPath, model_size + "/accuracy_score", score)
    else : 
        # print("Mots manquants dans la transcription de fw :", missedWords)
        print("Score of audio transcriptions of '%s' : %d/%d = %.2f" % (getFileName(audioPath), (total_mots - cpt), total_mots, score))

    return score


def processAudio(audioPath, fw_model, record=False):
    '''
    Takes an audio file, makes the transcription with faster-whisper, saves the
    transcription into a file and gives it a score that is saved into accuracy_score.txt file

    Args:
        audioPath : str - file path of the audio file to process
        fw_model : str - name of the model used to process the audio files
        record : bool - if True it writes the data into a file, else just prints it on the terminal
    '''
    getTranscript(audioPath, fw_model, record)
    getScore(audioPath, None, fw_model, record)
    print("Finished avualiting : '%s'" % getFileName(audioPath))

def processAudiowNoise(audioPath, fw_model, record=False):
    '''
    Takes an audio file with voice percentage, makes the transcription with faster-whisper, saves the
    transcription into a file and gives it a score that is saved into accuracy_score.txt file

    Args:
        audioPath : str - file path of the audio file to process
        fw_model : str - name of the model used to process the audio files
        record : bool - if True it writes the data into a file, else just prints it on the terminal
    '''
    getTranscript(audioPath, fw_model, record)
    name = re.split(r"[-/.]",audioPath)[-3]
    og_file = "transcriptions/original/og_" + name +".txt"
    getScore(audioPath, og_file, fw_model, record=True)
    print("Finished avualiting : '%s'" % getFileName(audioPath))


def processAllAudio(fw_model, directory = "samples"):
    '''
    Processes of all the audio files found in 'directory', the data would be automatically be 
    recorded into the files 'exec_time.txt' and 'accuracy_score.txt'

    Args:
        fw_model : str - name of the model used to process the audio files
        directory : str - directory path where the audio files are located
    '''
    data_dir = "data/" + fw_model
    if os.path.exists(data_dir + "/exec_time.txt") :
        os.remove(data_dir + "/exec_time.txt")
    if os.path.exists(data_dir + "/comparison_exec_time.txt") :
        os.remove(data_dir + "/comparison_exec_time.txt")
    if os.path.exists(data_dir + "/accuracy_score.txt"):
        os.remove(data_dir + "/accuracy_score.txt")

    files = glob.glob(directory + "/*.m4a") + glob.glob(directory + "/*.mp3")
    for audioPath in files :
        processAudio(audioPath, fw_model, record=True)
    
    files = glob.glob("samples/withNoise/*.mp3")
    for audioNoise in files:
        processAudiowNoise(audioNoise, fw_model, record=True)

def getFileName(filePath):
    '''
    Returns the name of the audio file (with noise level indicator)
    '''
    return re.split(r"[/.]",filePath)[-2]


# Plotting stuff #

def plotScore(models):
    '''
    Args:
        models : list of str of models sizes that are gonna be plotted
    '''
    # scores = {noise : [] for noise in range(0, 101, 10)}
    results = {mod : {noise : [] for noise in range(0, 101, 10)} for mod in models}

    # Plot definition
    plt.figure(figsize=(10,7))
    xvalues = range(0,101,10)
    # plt.title("Score median by noise percentage")
    plt.title("Score median by noise percentage\nA comparison by model size of Faster-Whisper")
    plt.xlabel("Noise level (%)")
    plt.ylabel("Transcription score (%)")
    
    withNoise = glob.glob("samples/withNoise/*.mp3")
    noNoise = []
    for model in models: 
        for f in withNoise:
            noise = int(re.split(r"[-/.]",f)[-2])
            name = re.split(r"[-/.]",f)[-3]
            og_file = "transcriptions/original/og_" + name +".txt"
            currentScore = getScore(f, og_file, model, record=False)
            results[model][noise].append(round(currentScore,2))

            if name not in noNoise :
                noNoise.append(name)

        for name in noNoise:
            audioPath = "samples/"+ name +".m4a"
            og_file = "transcriptions/original/og_"+ name+".txt"
            currentScore = getScore(audioPath,og_file, model, record=False)
            results[model][0].append(round(currentScore, 2))

        # Creating plot data 
        data = []
        q1 = []
        q3 = []
        for i in range(0, 101, 10):
            data.append(np.mean(results[model][i]))
            q1.append(np.quantile(results[model][i],0.25))
            q3.append(np.quantile(results[model][i],0.75))
        
        plt.plot(xvalues, data, marker='o', linestyle='-', label=model)
        plt.fill_between(xvalues, q1, q3, alpha = 0.2)
    
    plt.plot(xvalues, [90 for _ in range(len(xvalues))], linestyle='--', label='baseline', color='black')
    plt.legend()
    plt.grid(True, alpha=0.2)
    # plt.show()

def plot_transcribe_times(models):
    '''
    Create a bar plot comparing transcribe execution times across different models
    
    Args:
        models: list of str - model sizes to compare
    '''
    plt.figure(figsize=(10, 6))
    colors = ['#3B75AF', '#EF8636', '#529E3F', '#C43A32']
    
    # Prepare data
    model_means = []
    model_stds = []
    
    for model in models:
        data = np.loadtxt(f"data/{model}/comparison_exec_time.txt")
        transcribe_times = data[:, 0]  # First column contains transcribe times
        
        model_means.append(np.mean(transcribe_times))
        model_stds.append(np.std(transcribe_times))
    
    # Create bar plot
    x = np.arange(len(models))
    bars = plt.bar(x, model_means, yerr=model_stds, capsize=5, alpha=0.8, color=colors[:len(models)])
    
    # Customization
    plt.title("Average Transcription Time by Model Size")
    plt.xlabel("Model Size")
    plt.ylabel("Time (seconds)")
    plt.xticks(x, models)
    
    # Add value labels on top of each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'   {height:.2f}s',
                ha='left', va='bottom')
    
    plt.grid(True, axis='y', alpha=0.3)


# MAIN #
def main():
    # Processes only one audio file, predetermined to have record = False to not polluate the data files, will print data in terminal
    # fw_model_size = "tiny"
    # fw_model_size = "small"
    # fw_model_size = "medium"
    fw_model_size = "large-v3"
    getTranscript("samples/juin.m4a", fw_model_size, record=False)
    # getScore("samples/juin.m4a", None, fw_model_size, record=False)

    print("Finished.")
    


if __name__ == "__main__":
    main()