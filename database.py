from dataclasses import dataclass
import math as maths
import sqlite3
import tf_idf
import nltk
import os

class DatabaseCursor(sqlite3.Cursor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

@dataclass
class Database:
    db_path:str = os.path.join(".", "wikibooks.db")

    def __enter__(self):
        if not os.path.exists(self.db_path):
            self.__connection = sqlite3.connect(self.db_path)
            self.__build_db()
        else:
            self.__connection = sqlite3.connect(self.db_path)

        self.__connection.create_function('log', 1, maths.log10)
        self.__connection.create_function("log_tf", 1, tf_idf.calc_log_tf)
        return self

    def __exit__(self, type, value, traceback):
        self.__connection.commit()
        self.__connection.close()

    def __build_db(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `documents` (
                `document_id` INTEGER PRIMARY KEY,
                `document_name` TEXT NOT NULL
            );""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `vocabulary` (
                `vocabulary_id` INTEGER PRIMARY KEY,
                `term` TEXT NOT NULL
            );""")
            # \/ VERY UGLY NOT HOW THOS SHOULD BE DONE
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `linked_terms` (
                `linked_term_id` INTEGER PRIMARY KEY,
                `chain` TEXT NOT NULL
            );""")
            cursor.execute("CREATE UNIQUE INDEX unique_chain on linked_terms (chain);")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `term_weights` (
                `term_weight_id` INTEGER PRIMARY KEY, 
                `vocabulary_id` INT UNSIGNED NULL,
                `linked_term_id` INT UNSIGNED NULL, 
                `document_id` INT UNSIGNED NOT NULL, 
                `weight` INT UNSIGNED NOT NULL, 
                FOREIGN KEY (`vocabulary_id`) REFERENCES `vocabulary`(`vocabulary_id`),
                FOREIGN KEY (`linked_term_id`) REFERENCES `linked_terms`(`linked_term_id`), 
                FOREIGN KEY (`document_id`) REFERENCES `documents`(`document_id`)
            );""")
            cursor.execute("CREATE UNIQUE INDEX unique_terms on vocabulary (term);")

    def append_documents(self, documents):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("INSERT INTO `documents` (document_name) VALUES (?);", [(doc, ) for doc in documents])

    def get_document_name_by_id(self, id_):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT `document_name` FROM `documents` WHERE `document_id` = ?;", (id_, ))
            return cursor.fetchone()[0]

    def get_document_id_by_name(self, document_name):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT `document_id` FROM `documents` WHERE `document_name` = ?", (document_name, ))
            return cursor.fetchone()[0]

    def get_num_documents(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT COUNT(*) FROM documents;")
            return cursor.fetchone()[0]

    def get_max_linked_terms(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT MAX(`document_id`) + 2 FROM term_weights;")
            return cursor.fetchone()[0]

    def append_terms(self, terms):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("INSERT OR IGNORE INTO vocabulary(term) VALUES (?);", [(term, ) for term in terms])

    def get_vocabulary_ids(self, terms):
        # can't do executemany with select statements :(
        out = {}
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            for term in terms:
                cursor.execute("SELECT `vocabulary_id` FROM `vocabulary` WHERE `term` = ?;", (term, )) 
                out[term] = cursor.fetchone()[0]
        return out

    def get_linked_vocabulary_ids(self, linked_term):
        ids = []
        print(linked_term)
        for term in linked_term:
            out.append(str(self.get_vocabulary_ids([term])[term]))
        print(",".join(ids))

        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT `vocabular")

    def append_merged_terms(self, merged_terms):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("INSERT OR IGNORE INTO `linked_terms`(`chain`) VALUES (?);", [(i, ) for i in merged_terms])

    def append_document_term_weights(self, terms, document_id):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("""
            INSERT INTO `term_weights` 
            (`vocabulary_id`, `linked_term_id`, `document_id`, `weight`)
            VALUES ((
                SELECT `vocabulary_id` FROM `vocabulary` WHERE `term` = ?
            ), NULL, ?, ?);
            """, [(i[0], document_id, i[1]) for i in terms.items()])

    def append_document_linked_term_weights(self, linked_terms, document_id):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("""
            INSERT INTO `term_weights` 
            (`vocabulary_id`, `linked_term_id`, `document_id`, `weight`)
            VALUES (NULL, (
                SELECT `linked_term_id` FROM `linked_terms` WHERE `chain` = ?
            ), ?, ?);
            """, [(i[0], document_id, i[1]) for i in linked_terms.items()])

    def build_tf_idf_table(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("DROP VIEW IF EXISTS `tf_idf_linked`;")
            cursor.execute("DROP VIEW IF EXISTS `tf_idf_singles`;")
            cursor.execute("DROP VIEW IF EXISTS `vocab_count_singles`;")
            cursor.execute("DROP VIEW IF EXISTS `vocab_count_linked`;")
            # i wish i could find a way to do this with a single view but alas i am
            # not good enough at SQL
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS `vocab_count_singles` AS 
            SELECT vocabulary_id, 
            COUNT(vocabulary_id) AS vocabulary_count
            FROM term_weights 
            GROUP BY vocabulary_id;
            """)
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS `tf_idf_singles` AS SELECT
            `term_weights`.`vocabulary_id` AS `vocabulary_id`,
            `document_id`,
            `term_weights`.`weight`,
            LOG_TF(`weight`) AS tf,
            (SELECT COUNT(`document_id`) FROM `documents`) AS n,
            `vocab_count_singles`.`vocabulary_count` AS df,
            (SELECT LOG(CAST(COUNT(`document_id`) AS REAL) / `vocab_count_singles`.`vocabulary_count`) FROM documents) AS idf,
            LOG_TF(`weight`) * (SELECT LOG(CAST(COUNT(`document_id`) AS REAL) / `vocab_count_singles`.`vocabulary_count`) FROM documents) AS tf_idf
            FROM `term_weights`
            INNER JOIN `vocab_count_singles`
            ON `vocab_count_singles`.`vocabulary_id` = `term_weights`.`vocabulary_id`
            ;""")
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS `vocab_count_linked` AS
            SELECT linked_term_id, 
            COUNT(linked_term_id) AS linked_term_count
            FROM term_weights 
            GROUP BY linked_term_id;
            """)
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS `tf_idf_linked` AS SELECT
            `term_weights`.`linked_term_id` AS `linked_term_id`,
            `document_id`,
            `term_weights`.`weight`,
            LOG_TF(`weight`) AS tf,
            (SELECT COUNT(`document_id`) FROM `documents`) AS n,
            `vocab_count_linked`.`linked_term_count` AS df,
            (SELECT LOG(CAST(COUNT(`document_id`) AS REAL) / `vocab_count_linked`.`linked_term_count`) FROM documents) AS idf,
            LOG_TF(`weight`) * (SELECT LOG(CAST(COUNT(`document_id`) AS REAL) / `vocab_count_linked`.`linked_term_count`) FROM documents) AS tf_idf
            FROM `term_weights`
            INNER JOIN `vocab_count_linked`
            ON `vocab_count_linked`.`linked_term_id` = `term_weights`.`linked_term_id`
            ;""")

    def get_term_frequencies(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT * FROM `term_weights`;")
            return cursor.fetchall()


    def test_log(self, to_log):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT LOG(?);", (to_log, ))
            return cursor.fetchone()

    def test_tf_log(self, to_tf):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT LOG_TF(?);", (to_tf, ))
            return cursor.fetchone()

    def get_tf_idf_table(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT * FROM `tf_idf_singles` LIMIT 100;")
            out = cursor.fetchall()
            print(len(out))
            print(("vocabulary_id", "document_id", "weight", "tf", "n", "df", "idf"))
            for l in out[:100]:
                print(l)

    def get_tf_idf_table2(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT * FROM `tf_idf_linked` LIMIT 100;")
            out = cursor.fetchall()
            for l in out[:100]:
                print(l)

    def get_tf_idf_score_single(self, term, tf_idf_thresh = 0, limit = 1000, multiplier = 1):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("""
            SELECT `document_id`, `tf_idf` FROM `tf_idf_singles` WHERE `vocabulary_id` = (
                SELECT `vocabulary_id` FROM `vocabulary` WHERE `term` = ?
            ) AND `tf_idf` > ? ORDER BY `tf_idf` DESC LIMIT ?;
            """, (term, tf_idf_thresh, limit))
            return {i[0]: maths.log10(i[1] * multiplier) for i in cursor.fetchall()}

    def get_tf_idf_score_linked(self, linked_term, tf_idf_thresh = 0, limit = 1000, multiplier = 1):
        word_ids = []
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            for word in linked_term:
                cursor.execute("SELECT `vocabulary_id` FROM `vocabulary` WHERE `term` = ?", (word, ))
                try:
                    word_ids.append(str(cursor.fetchone()[0]))
                except TypeError:
                    continue
        
            chain = ",".join(word_ids)

            cursor.execute("""
            SELECT `document_id`, `tf_idf` FROM `tf_idf_linked` WHERE `linked_term_id` = (
                SELECT `linked_term_id` FROM `linked_terms` WHERE `chain` = ?
            ) AND `tf_idf` > ? ORDER BY `tf_idf` DESC LIMIT ?;
            """, (chain, tf_idf_thresh, limit))
            return {i[0]: maths.log10(i[1] * multiplier) for i in cursor.fetchall()}

    def attempt_get_linked_words(self, words):
        word_ids = []
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            for word in words:
                cursor.execute("SELECT `vocabulary_id` FROM `vocabulary` WHERE `term` = ?", (word, ))
                try:
                    word_ids.append(str(cursor.fetchone()[0]))
                except TypeError:
                    continue
        
            combinations = [",".join(word_ids)]
            for n in range(2, len(word_ids)):
                combinations += [",".join(i) for i in nltk.ngrams(word_ids, n)]
            # print(combinations)

            if len(combinations) == 0:
                return []
            elif len(combinations) == 1:
                sql =  "SELECT `chain` FROM `linked_terms` WHERE `chain` = '%s';" % combinations[0]
            else:
                sql = "SELECT `chain` FROM `linked_terms` WHERE `chain` IN %s;" % str(tuple(combinations))
            # print(sql)
            cursor.execute(sql)
            found_ids = [i[0].split(",") for i in cursor.fetchall()]

        return [[self.get_term_by_id(j) for j in i] for i in found_ids]

    def get_term_by_id(self, id_):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT `term` FROM `vocabulary` WHERE `vocabulary_id` = ?;", (id_, ))
            return cursor.fetchone()[0]       

if __name__ == "__main__":
    with Database() as db:
        # print(db.get_num_documents())
        # print(db.get_document_name_by_id(69420))
        # print(db.get_document_id_by_name("../Datasets/Wikibooks/Russian Lesson 2.html"))
        # print(db.test_log(100))
        # print(db.test_log(21))
        # db.get_tf_idf_table()
        #for i, v in db.get_tf_idf_score("enzyme", 1).items():
        #    print(i, v)
        print(db.attempt_get_linked_words(["a", "computer", "science"]))
