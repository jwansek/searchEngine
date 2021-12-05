from nltk.tokenize import sent_tokenize, word_tokenize
import documents
import datetime
import time
import bs4
import os
import re


def write(search_terms, results, timetaken, expanded_terms):

    out_path = os.path.join("searches", "search_%s-%f.md" % ("+".join(expanded_terms)[:20], time.time()))

    with open(out_path, "w", encoding='utf-8') as f:
        f.write("# Search %s\n" % str(datetime.datetime.now()))
        f.write("**Using search terms: %s**\n" % " ".join(search_terms))
        f.write("*Found %d results in %.2f minutes*\n\n" % (len(results), timetaken / 60))

        for docid, score in results[:30]:
            fullpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), documents.get_document_name_by_id(docid))
            title, ext = os.path.splitext(os.path.split(fullpath)[-1])
            f.write("### %.2f - [%s](file://%s) [%s]\n" % (score, title, fullpath, ext[1:].upper()))
            f.write("###### *%s*\n" % fullpath)
            f.write("%s\n" % get_snippet(fullpath, expanded_terms))

            f.write("\n")

    return out_path

def get_snippet(docpath, expanded_terms, num_to_get = 2):
    with open(docpath, "r", encoding='utf-8') as f:
       soup = bs4.BeautifulSoup(f.read(), "lxml")

    text = " ".join([e.text for e in soup.find("div", {"class": "mw-parser-output"}).findChildren(recursive = True)])
    found_sentences = []
    for sentence in sent_tokenize(text):
        if len(found_sentences) == num_to_get:
            break

        found_terms = re.search("|".join(expanded_terms), sentence, re.IGNORECASE)
        if found_terms is not None:
            sentence = shorten_sentence(sentence, expanded_terms)
            new_sentence = sentence
            for match in re.finditer("|".join(expanded_terms), sentence, re.IGNORECASE):
                if not new_sentence[match.start() - 4:match.start()].startswith("*"):
                    new_sentence = new_sentence.replace(match.group(0), "**" + match.group(0) + "**").replace("\n", " ")

            found_sentences.append(new_sentence)

    return "*[...]* " + "\t*[...]*\t".join(found_sentences) + " *[...]*"

def shorten_sentence(sentence, expanded_terms):
    if len(sentence) > 200:
        match = re.search("|".join(expanded_terms), sentence, re.IGNORECASE)
        add_to_end = 0
        startindex = match.start() - 106
        if startindex < 0:
            add_to_end += abs(startindex)
            startindex = 0

        endindex = match.end() + 106 + add_to_end
        return " ".join(word_tokenize(sentence[startindex:endindex])[1:-1])
    else:
        return sentence

if __name__ == "__main__":
    # print(get_snippet("../Wikibooks/Wikibooks/History of video games Print version Timeline.html", ['cosmonaut', 'astronaut', 'spaceman']))

    print(shorten_sentence('star cloud") maryan....constellation   ("collection of stars") marmeg....comet   ("star rock") mommeg....meteor   ("space rock") mammeg....meteorite   ("sky rock") The following are vehicles and derivatives that are specific to one of the above physical spheres: Vehicles Specific to Various Spheres mompur....spaceship momper....travel through space momput....cosmonaut, astronaut mampur....airplane mamper....fly mamput....flyer, pilot mempur....automobile memper....ride, drive memput....rider, driver mimpur....shipobmimpar....submarine mimper....sail, navigate mimput....sailor, navigatorobmimput....submariner mumpur....subway mumper....tunnel, go by metro mumput....metro rider Note: marpur = starship and muarpur = lunar module Names of the Planets[edit | edit source] Here are the names of the planets in our solar system.', ["cosmonaut", 'astronaut', 'spaceman']))