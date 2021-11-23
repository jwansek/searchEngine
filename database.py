from dataclasses import dataclass
import math as maths
import sqlite3
import tf_idf
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
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `term_frequency` ( 
                `vocabulary_id` INT UNSIGNED NOT NULL, 
                `document_id` INT UNSIGNED NOT NULL, 
                `frequency` INT UNSIGNED NOT NULL, 
                FOREIGN KEY (`vocabulary_id`) REFERENCES `vocabulary`(`vocabulary_id`), 
                FOREIGN KEY (`document_id`) REFERENCES `documents`(`document_id`), 
                PRIMARY KEY(`vocabulary_id`, `document_id`) 
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

    def append_terms(self, terms):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("INSERT OR IGNORE INTO vocabulary(term) VALUES (?);", [(term, ) for term in terms])

    def append_terms_in_document(self, document_id, counter):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("""
            INSERT INTO `term_frequency`(`vocabulary_id`, `document_id`, `frequency`) 
            VALUES ((SELECT `vocabulary_id` FROM `vocabulary` WHERE `term` = ?), ?, ?)
            """, [(i[0], document_id, i[1]) for i in counter.items()])

    def build_tf_idf_table(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            # cursor.execute("DROP VIEW IF EXISTS `tf_idf`;")
            # cursor.execute("DROP VIEW IF EXISTS `vocab_count`;")
            # i wish i could find a way to do this with a single view but alas i am
            # not good enough at SQL
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS `vocab_count` AS 
            SELECT vocabulary_id, 
            COUNT(vocabulary_id) AS vocabulary_count
            FROM term_frequency 
            GROUP BY vocabulary_id;
            """)
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS `tf_idf` AS SELECT
            `term_frequency`.`vocabulary_id` AS `vocabulary_id`,
            `document_id`,
            `term_frequency`.`frequency`,
            LOG_TF(`frequency`) AS tf,
            (SELECT COUNT(`document_id`) FROM `documents`) AS n,
            `vocab_count`.`vocabulary_count` AS df,
            (SELECT LOG(CAST(COUNT(`document_id`) AS REAL) / `vocab_count`.`vocabulary_count`) FROM documents) AS idf,
            LOG_TF(`frequency`) * (SELECT LOG(CAST(COUNT(`document_id`) AS REAL) / `vocab_count`.`vocabulary_count`) FROM documents) AS tf_idf
            FROM `term_frequency`
            INNER JOIN `vocab_count`
            ON `vocab_count`.`vocabulary_id` = `term_frequency`.`vocabulary_id`
            ;""")

    def get_term_frequencies(self):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("SELECT * FROM `term_frequency`;")
            return cursor.fetchall()

    def append_tf_idf_table(self, tfs):
        # print([(i[0], i[1], i[2], i[0], i[0], i[2]) for i in tfs][1])
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.executemany("""
            INSERT INTO `tf_idf`(`vocabulary_id`, `document_id`, `tf`, `idf`, `tf_idf`)
            VALUES (
                ?, ?, ?, 
                (SELECT log((SELECT CAST(COUNT(*) as REAL) FROM documents) / COUNT(*)) FROM term_frequency WHERE vocabulary_id = ?),
                (SELECT log((SELECT CAST(COUNT(*) as REAL) FROM documents) / COUNT(*)) FROM term_frequency WHERE vocabulary_id = ?) * ?)
            """, [(i[0], i[1], i[2], i[0], i[0], i[2]) for i in tfs])

    def append_tf_idf_table_single(self, vocabulary_id, document_id, tf):
        with self.__connection.cursor(factory = DatabaseCursor) as cursor:
            cursor.execute("""
            INSERT INTO `tf_idf`(`vocabulary_id`, `document_id`, `tf`, `idf`, `tf_idf`)
            VALUES (
                ?, ?, ?, 
                (SELECT log((SELECT CAST(COUNT(*) as REAL) FROM documents) / COUNT(*)) FROM term_frequency WHERE vocabulary_id = ?),
                (SELECT log((SELECT CAST(COUNT(*) as REAL) FROM documents) / COUNT(*)) FROM term_frequency WHERE vocabulary_id = ?) * ?)
            """, (vocabulary_id, document_id, tf, vocabulary_id, vocabulary_id, tf))

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
            cursor.execute("SELECT * FROM `tf_idf` LIMIT 100;")
            out = cursor.fetchall()
            print(len(out))
            print(("vocabulary_id", "document_id", "frequency", "tf", "n", "df", "idf"))
            for l in out[:100]:
                print(l)

if __name__ == "__main__":
    with Database() as db:
        # print(db.get_num_documents())
        # print(db.get_document_name_by_id(69420))
        # print(db.get_document_id_by_name("../Datasets/Wikibooks/Russian Lesson 2.html"))
        # print(db.test_log(100))
        # print(db.test_log(21))
        db.get_tf_idf_table()