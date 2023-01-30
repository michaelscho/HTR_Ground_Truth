import json # for handling JSON data
import pandas as pd # for handling data
import re # for handling regex
import config # for basic configuration
import os # for handling files on system
from csv import DictWriter # for writing CSV files from dictionaries
import lxml.etree as LET # For handling pageXML



def load_pagexml(path):
    """ Get path to pageXML files for further processing

    :param folder_name: Takes path to pageXML as returned by unzip_file()
    :return: Returns path to pageXML files as list
    """
    print(path)
    filenames = next(os.walk(path), (None, None, []))[2]
    path_to_pages = sorted([path + '/' + string for string in filenames])
    return path_to_pages

def get_unique_words(page):
    # prepare list to store unique words
    unique_words = []
    # parse as xml
    tree = LET.parse(page)
    # get root
    root = tree.getroot()
    # get textregions
    textregions = root.xpath('//ns0:TextRegion', namespaces = {'ns0':'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'})
    # iterate through textregion and get lines     
    for textregion in textregions:
        lines = textregion.xpath('.//ns0:TextLine//ns0:Unicode', namespaces = {'ns0':'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'})
        for line in lines:
            # get words
            line_text = line.text
            # delete characters such as interpunctuation as specified in config.py
            for character in config.characters_to_clean:
                line_text = line_text.replace(character, '')
            if " " in line_text:
                words = line_text.split(" ")
                for word in words:
                    # add word to wordlist
                    unique_words.append(word)
            else: 
                unique_words.append(line_text)
    # delete duplettes
    unique_words = list(set(unique_words))
    # delete roman numerals if indicated by special character
    unique_words = [x for x in unique_words if "\u033F" not in x]
    print(unique_words)
    return unique_words

def expand_pagexml(path, domain_dictionary, dictionary):
    # create dictionary storing abbreviations
    abbreviation_dict = {}
    # get path to single pagexml files
    path_to_pages = load_pagexml(path)
    # iterate through files and expand abbreviations
    for page in path_to_pages:
        # open pagexml as textfile to replace words
        with open(page,"r", encoding="utf8") as page_xml:
            file = page_xml.read()
        unique_words = get_unique_words(page)
        for word in unique_words:
            # Check if word is abbreviated using predefined special characters ...
            if any(character in config.special_characters for character in word):
                # ... try expansion by domain specific wordlist ...
                if word in domain_dictionary:
                    #... and get corresponding expansion if found in dictionary.
                    expansion = domain_dictionary[word]
                # ... orhewise try expansion by general wordlist ...
                elif word in dictionary:
                    #... and get corresponding expansion if found in dictionary.
                    expansion = dictionary[word]
                # Otherwise perform expansion by rules ...
                else:
                    expansion = word
                    # ... iterate through rules for expansion and replace special characters
                    for key, value in config.rules_for_expansion.items():
                        expansion = expansion.replace(key,value)

                # replace word in file
                for character in config.characters_to_clean:
                    file = file.replace(" " + word + character, " " + expansion + character)
                    file = file.replace(">" + word + character, ">" + expansion + character)
                    file = file.replace(character + word + " ", character + expansion + " ")
                    file = file.replace(character + word + "<", character + expansion + "<")
                    
                file = file.replace(" " + word + " ", " " + expansion + " ")
                file = file.replace(" " + word + "<", " " + expansion + "<")
                file = file.replace(">" + word + " ", ">" + expansion + " ")

                # add abbreviation to list
                abbreviation_and_expandion = {word:expansion}
                abbreviation_dict.update(abbreviation_and_expandion)
        
        # write expanded pagexml into expanded folder
        with open(page.replace('base', 'expanded'), 'w', encoding="utf8") as new_file:
            new_file.write(file)

        # create json file for storing abbreviations     
        with open("../data/expanded_abbreviations.json","w") as jsonfile:
            # parsing JSON string:
            json.dump(abbreviation_dict, jsonfile, indent = 4)

def load_data(path_to_lexicon):
    """ Load local copy of Frankfurt Latin Lexicon

    Load local copy of Frankfurt Latin Lexicon as pandas dataframe for further processing in chunks to cope with large file.
    File uses tabs as separator.

    :return df: Lexicon as pandas dataframe.
    """

    # Load lexicon as pandas dataframe in chunks due to its size
    chunk = pd.read_csv(path_to_lexicon, sep='\t', on_bad_lines='skip', chunksize=100000)
    df = pd.concat(chunk)
    return df

        
def normalize_pagexml(path, path_to_lexicon):
    # load lexicon
    df = load_data(path_to_lexicon)
    # get path to single pagexml files
    path_to_pages = load_pagexml(path)
    # iterate through files and expand abbreviations
    for page in path_to_pages:
        # open pagexml as textfile to replace words
        with open(page,"r", encoding="utf8") as page_xml:
            file = page_xml.read()
        unique_words = get_unique_words(page)
        for word in unique_words:
            word_to_test = word

            if df['WF-Name'].eq(word_to_test.lower()).any():
                # Get superlemma of that row
                superlemma = df.loc[df['WF-Name'] == word_to_test.lower(), 'SL-Name'].array[0]
                # Get lemma of that row
                lemma = df.loc[df['WF-Name'] == word_to_test.lower(), 'L-Name'].array[0]

                # add some stopwords
                if superlemma == "alea@NN" or superlemma == "a@AP" or superlemma == "hilla@NN":
                    continue
                if superlemma.split("@")[0][-1:] != lemma[-1:]:
                    print("Fehler in Lemma oder Superlemma: " + superlemma, lemma)
                    continue

                # create dictionary with word, lemma and superlemma
                dict_normalization = {"Wort": word, "Superlemma": superlemma, "Lemma": lemma}
                
                # Delete last character to get root of word
                wordform = superlemma.split("@")[1]

                # decide wordform to deduce root of word
                if wordform == 'V':
                    superlemma = superlemma.split("@")[0]
                    if superlemma.endswith('or'):
                        chars_to_delete = -2
                    elif superlemma.endswith('sco'):
                        chars_to_delete = -3
                    else:
                        chars_to_delete = -1
                    superlemma = superlemma[:chars_to_delete] # replace last char to get root
                    lemma = lemma[:chars_to_delete] # replace last char to get root
                elif wordform == 'ADV':
                    superlemma = superlemma.split("@")[0] # take as it is
                    lemma = lemma # take as it is
                elif wordform == 'PRO':
                    if superlemma.endswith('er'):
                        chars_to_delete = -2
                    else:
                        chars_to_delete = -1

                    superlemma = superlemma.split("@")[0][:chars_to_delete] # replace last char to get root
                    lemma = lemma[:chars_to_delete] # replace last char to get root

                else:
                    superlemma = superlemma.split("@")[0]
                    endings = ["um", "us", "u", "e", "os", "a", "us", "is", "es", "as"] 
                    for ending in endings:
                        if superlemma.endswith(ending):
                            superlemma = superlemma[:-len(ending)]
                            lemma = lemma[:-len(ending)]

                # update dictionary with manipulated forms
                dict_normalization.update({"Superlemma_root": superlemma, "Lemma_root": lemma, "Wortform": wordform}) 

                # check if word started with capital
                if word[0].isupper():
                    lemma = lemma.capitalize() 
                    superlemma = superlemma.capitalize() 

                # Normalise word by replacing lemma with superlemma
                normalised_word = word.replace(lemma, superlemma)

                # normalise endings of verbs
                if wordform == 'V':
                    ending = normalised_word.replace(superlemma, '')
                    for word_ending in config.verb_endings_to_normalise:
                        normalised_word = normalised_word.replace(word_ending[0], word_ending[1])
                
                # update dictionary with manipulated forms
                dict_normalization.update({"Normalisierung": normalised_word}) 

                
                # replace word in file
                for character in config.characters_to_clean:
                    file = file.replace(" " + word + character, " " + normalised_word + character)
                    file = file.replace(">" + word + character, ">" + normalised_word + character)
                    file = file.replace(character + word + " ", character + normalised_word + " ")
                    file = file.replace(character + word + "<", character + normalised_word + "<")
                    
                file = file.replace(" " + word + " ", " " + normalised_word + " ")
                file = file.replace(" " + word + "<", " " + normalised_word + "<")
                file = file.replace(">" + word + " ", ">" + normalised_word + " ")
        
        # write expanded pagexml into expanded folder
        with open(page.replace('expanded', 'normalized'), 'w', encoding="utf8") as new_file:
            new_file.write(file)


def main():
    # Set path to Ground Truth
    paths_to_base_ground_truth = ["../data/Munich_BSB_Clm_14733/base/page", "../data/Vienna_ÖNB_Cod_12600/base/page"]   
    # Set path to abbreviation dictionary and open
    path_to_domain_specific_abbreviation_dictionary = "../resources/expanded_abbreviations.json"
    with open(path_to_domain_specific_abbreviation_dictionary,'r', encoding="utf8") as json_file:
        domain_dictionary = json.load(json_file)
    path_to_abbreviation_dictionary = '../resources/abbreviation_dictionary.json'
    with open(path_to_abbreviation_dictionary,'r', encoding="utf8") as json_file:
        dictionary = json.load(json_file)
    # Set path to latin dictionary
    path_to_lexicon = '../resources/frankfurt_latin_lexicon.txt'


    for path in paths_to_base_ground_truth:
        #expand_pagexml(path, domain_dictionary, dictionary)
        normalize_pagexml(path.replace("base","expanded"), path_to_lexicon)    

if __name__ == "__main__":
    main()

