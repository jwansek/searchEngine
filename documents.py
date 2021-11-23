import database
import sys
import os

def add_documents(documents_path):
    docs = [os.path.join(documents_path, f) for f in os.listdir(documents_path)]
    print(docs)
    with database.Database() as db:
        db.append_documents(docs)

def get_document_name_by_id(id_):
    with database.Database() as db:
        return db.get_document_name_by_id(id_)

def get_document_id_by_name(document_name):
    with database.Database() as db:
        return db.get_document_id_by_name(document_name)

def get_num_documents():
    with database.Database() as db:
        return db.get_num_documents()        

if __name__ == "__main__":
    add_documents(sys.argv[1])

    # print(get_document_name_by_id(1))
    # print(get_document_id_by_name("../Wikibooks/USMLE Step 1 Review Reproductive.html"))
    # print(get_num_documents())