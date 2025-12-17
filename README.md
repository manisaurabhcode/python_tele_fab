# python_tele_fab
sample repo
Prerequisite
Python 2.6 or higher is usually required for installation of Flask. Although Flask and its dependencies work well with Python 3 (Python 3.3 onwards), many Flask extensions do not support it properly. Hence, it is recommended that Flask should be installed on Python 2.7.

Install virtualenv for development environment
virtualenv is a virtual Python environment builder. It helps a user to create multiple Python environments side-by-side. Thereby, it can avoid compatibility issues between the different versions of the libraries.

The following command installs virtualenv

pip install virtualenv
This command needs administrator privileges. Add sudo before pip on Linux/Mac OS. If you are on Windows, log in as Administrator. On Ubuntu virtualenv may be installed using its package manager.

Sudo apt-get install virtualenv
Once installed, new virtual environment is created in a folder.
11AQZKNJY0I6LWwinbTlIx_v3GjeCxVcSHqVS0CF7cNn4ECyhkjbgJjA1ZWOKQQMBN65SIRJXJ1C2Va1rz
mkdir newproj
cd newproj
virtualenv venv
To activate corresponding environment, on Linux/OS X, use the following −

venv/bin/activate
On Windows, following can be used

venv\scripts\activate
We are now ready to install Flask in this environment.

pip install Flask
The above command can be run directly, without virtual environment for system-wide installation.

Then add main.py file in your repo.

Run using python main.py.
Sample curl:
curl --location --request POST 'http://localhost:5000/sn/gesw/sc1' \
--header 'Content-Type: application/json' \
--header 'Authorization: Basic cmVzdC53c28yOlBhc3N3b3JkQDEyMw==' \
--data-raw '{
  "u_project_number": "as",
  "u_gesw_number": "asd"
}'
