# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student from an activity                           |

## Data Model

The application uses a persistent SQLite data model (`src/data/school.sqlite`) with meaningful identifiers:

1. **Users** - Uses email as identifier:

   - Role (`student_viewer` by default)

2. **Clubs** - Groups activities under a shared domain:

   - Name
   - Description

3. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - Club relationship

4. **Enrollments** - Links users to activities:
   - Prevents duplicate signups at the DB level
   - Enables persistent participant tracking

## Initialization Strategy

- On startup, the app creates tables if they do not exist.
- If the activities table is empty, the app seeds initial activities and participant enrollments.
- Existing databases are left intact, so data survives server restarts.
