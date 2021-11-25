import database
import logging
import terms
import sys
import re

logging.basicConfig(
    format = "[%(asctime)s]\t%(message)s",
    level = logging.INFO,
    handlers=[
        logging.FileHandler("searches.log"),
        logging.StreamHandler()
])

def main(search_words):
    
    txt = [re.sub(r"[^a-zA-Z\s]", "", i).rstrip().lower() for i in search_words]
    
    search_words = []
    for i in txt:
        search_words += re.split(r"\s+|\n", i)
    
    search_words = [terms.LEM.lemmatize(i) for i in search_words if i != "" and i not in terms.STOPWORDS]
    logging.info("Started searching. Using terms: %s" % " ".join(search_words))

    with database.Database() as db:
        tf_idf_scores = []
        for term in search_words:
            tf_idf_scores.append(db.get_tf_idf_score(term, tf_idf_thresh = 1, limit = 1000))
            logging.info("Fetched %d scores for term '%s'..." % (len(tf_idf_scores[-1]), term))

        merged_scores = {i: 0 for i in range(1, db.get_num_documents() + 1)}
        for scorelist in tf_idf_scores:
            for doc_id, score in scorelist.items():
                merged_scores[doc_id] += score
        logging.info("Merged scores...")

        sorted_scores = list(reversed(sorted(merged_scores.items(), key = lambda i: i[1])))
        toshow = 30
        logging.info("Sorted scores...")

        for i, j in enumerate(sorted_scores, 0):
            if i >= toshow:
                break

            docid, score = j
            logging.info("%.2f - %d - %s" % (score, docid, db.get_document_name_by_id(docid)))

    logging.info("%d results found in total" % len([i[1] for i in sorted_scores if i[1] > 0.1]))    
        
        
if __name__ == "__main__":
    main(sys.argv[1:])
