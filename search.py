import terms
import sys
import re

def main(search_words):
    
    txt = [re.sub(r"[^a-zA-Z\s]", "", i).rstrip().lower() for i in search_words]
    
    search_words = []
    for i in txt:
        search_words += re.split(r"\s+|\n", i)
    
    search_words = [terms.LEM.lemmatize(i) for i in search_words if i != "" and i not in terms.STOPWORDS]

    print(search_words)

if __name__ == "__main__":
    main(sys.argv[1:])