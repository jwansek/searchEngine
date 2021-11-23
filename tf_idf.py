import math as maths
import database

def main():
    with database.Database() as db:
        db.build_tf_idf_table()

        db.get_tf_idf_table()

def calc_log_tf(tf):
    if tf == 0:
        return 0
    else:
        return maths.log10(1 + tf)

if __name__ == "__main__":
    main()