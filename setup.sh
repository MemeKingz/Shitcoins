if [ ! -d "venv/" ]
then
        echo "Creating virtual environment venv..."
        python3 -m venv venv
        chmod +x venv/bin/activate
        . ./venv/bin/activate
else
        echo "Virtualenv venv already exists, activating..."
        . ./venv/bin/activate
fi

pip install --upgrade pip

pip install bump2version
pip install -e .
