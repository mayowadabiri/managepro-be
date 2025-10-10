PYTHON= uv run python

app:
ifndef NAME
	$(error Please provide NAME, e.g. make app NAME=blog)
endif
	$(PYTHON) manage.py startapp $(NAME)

run:
	$(PYTHON) manage.py runserver

migrate:
	$(PYTHON) manage.py migrate
	

makemigrations:
	$(PYTHON) manage.py makemigrations


createsuperuser:
	$(PYTHON) manage.py createsuperuser