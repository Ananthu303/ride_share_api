# Ride Sharing Application

## Overview

This is a ride-sharing application built with Django and Django REST Framework. It allows users to register as riders or drivers, create ride requests, and manage their rides. The application also includes real-time location updates and WebSocket support for enhanced user experience.

## Features

- User authentication (registration and login)
- Role-based access for riders and drivers
- Create, update, cancel, and list ride requests
- Drivers can view and accept nearby ride requests
- API endpoints for updating the status of a ride
- Real-time location tracking using WebSocket

## Technologies Used

- Django
- Django REST Framework
- Django Channels (for WebSocket support)
- JSON Web Tokens (JWT) for authentication

## Installation

1. Clone the repository:
   git clone https://github.com/Ananthu303/ride_share_api.git


2. Navigate to the project directory:

    cd rideshare

    ## Create a virtual environment:

        python -m venv venv

    ## Activate the virtual environment:

    ## On Windows:
        venv\Scripts\activate

    ## On macOS/Linux:
        source venv/bin/activate

3. Install the required packages:

    pip install -r requirements.txt

4. Set up the database:

    ## Update your database settings in settings.py.
    ## currently using db.sqlite3
    Run the migrations:

    python manage.py makemigrations
    python manage.py migrate

5. Run the development server:

    python manage.py runserver