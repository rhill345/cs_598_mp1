from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def compare_similarity(sentence1, sentence2):
    return fuzz.ratio(sentence1, sentence2)

if __name__ == "__main__":
    print compare_similarity("weather", " game theory")