from nltk.corpus import wordnet
from nltk import pos_tag
import markdown_renderer
import reportWriter
import collections
import itertools  
import database
import logging
import terms
import time
import sys
import re

logging.basicConfig(
    format = "[%(asctime)s]\t%(message)s",
    level = logging.INFO,
    handlers=[
        logging.FileHandler("searches.log"),
        logging.StreamHandler()
])

WORDNET_POS_MAP = {
    'NN': wordnet.NOUN,          
    'NNS': wordnet.NOUN,                 
    'NNP': wordnet.NOUN,        
    'NNPS': wordnet.NOUN,
    'JJ': [wordnet.ADJ, wordnet.ADJ_SAT],
    'JJS': [wordnet.ADJ, wordnet.ADJ_SAT],
    'RB': wordnet.ADV,    
    'RBR': wordnet.ADV,        
    'RBS': wordnet.ADV,     
    'RP': [wordnet.ADJ, wordnet.ADJ_SAT], 
    'VB': wordnet.VERB,
}

def main(search_words):
    starttime = time.time()
    pos_tags = [(token, tag) for token, tag in pos_tag(search_words) if token.lower().replace(",", "") not in terms.STOPWORDS]

    single_terms = [w.lower() for w in search_words]
    logging.info("Started with the terms: %s" % str(single_terms))
    with database.Database() as db:
        l = db.attempt_get_linked_words(single_terms)
    linked_terms = collections.Counter([",".join(i) for i in l])
    # do again so we get a weight of 2
    linked_terms += collections.Counter([",".join(i) for i in l])
    logging.info("Found the linked terms: %s" % str(l))

    synsets = [wordnet.synsets(token, WORDNET_POS_MAP[tag]) for token, tag in pos_tags if WORDNET_POS_MAP.__contains__(tag)]
    synonyms = list(itertools.chain.from_iterable([[lemma.name().lower().replace("_", ",") for syn in synset for lemma in syn.lemmas()] for synset in synsets]))

    # for syn in synsets:
    #     for sy in syn:
    #         print([w for s in sy.closure(lambda s:s.hyponyms()) for w in s.lemma_names()])

    for synonym in synonyms:
        if len(synonym.split(",")) > 1:
            linked_terms[synonym] = 1
        else:
            single_terms.append(synonym)

    single_terms = collections.Counter(single_terms)

    logging.info("Expanded single terms to: %s" % str(single_terms))
    logging.info("Expanded linked terms to: %s" % str(linked_terms))
    logging.info("\n\n")

    with database.Database() as db:
        tf_idf_scores = collections.Counter()
        for single_term, search_weight in single_terms.items():
            scores = collections.Counter(db.get_tf_idf_score_single(single_term, tf_idf_thresh = 1, limit = 1000, multiplier = search_weight))
            logging.info("Got %d scores for term '%s' (multiplier %d)" % (len(scores), single_term, search_weight))
            tf_idf_scores += scores

        for linked_term, search_weight in linked_terms.items():
            scores = db.get_tf_idf_score_linked(linked_term.split(","), tf_idf_thresh=0, multiplier=search_weight)
            logging.info("Got %d scores for linked term '%s' (multiplier %d)" % (len(scores), str(linked_term), search_weight))
            tf_idf_scores += scores
        
        sorted_scores = list(reversed(sorted(tf_idf_scores.items(), key = lambda i: i[1])))
        toshow = 30
        logging.info("Sorted scores...")
        logging.info("Results:\n\n")

        for docid, score in sorted_scores[:30]:
            logging.info("%.2f - %d - %s" % (score, docid, db.get_document_name_by_id(docid)))

    timetaken = time.time() - starttime
    logging.info("Got %d results in total. Took %.2f minutes (%.2fs per term)" % (len(tf_idf_scores), timetaken / 60, timetaken / (len(single_terms) + len(linked_terms))))
    md_path = reportWriter.write(sys.argv[1:], sorted_scores, timetaken, list(single_terms.keys()) + [i.replace(",", " ") for i in linked_terms.keys()])
    logging.info("Report written to %s..." % md_path)
        
    markdown_renderer.render_and_view(md_path)
    logging.info("Report rendered as HTML and showing..")

if __name__ == "__main__":
    main(sys.argv[1:])