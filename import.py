import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
	f = open("books.csv")
	reader = csv.reader(f)
	i = 0
	print("Starting Import...")
	for isbn_no, title, author_name, year in reader:
		db.execute("INSERT INTO authors (author_name) VALUES (:author_name)", {"author_name": author_name})
		db.execute("INSERT INTO books (title, year) VALUES (:title, :year)", {"title":title, "year" :year})
		author = db.execute("SELECT * from authors WHERE author_name = :author_name",
				{"author_name":author_name}).fetchone()
		
		book = db.execute("SELECT * from books WHERE title = :title",
				{"title":title}).fetchone()
		db.execute("INSERT INTO isbn (isbn_no, author_id, book_id) VALUES (:isbn_no, :author_id, :book_id) ",
			{"isbn_no":isbn_no, 
			"author_id":author['id'],
			"book_id": book['id'],
 			}
		)
		if(i % 100 == 0):
			print("Done", i)
		i += 1
	print("Done")
	db.commit()



if __name__ == "__main__":
	print("starting..")
	main()