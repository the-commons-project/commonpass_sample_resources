python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
python DSTU2.py lab_a_config.json
python DSTU2.py lab_b_config.json
deactivate
rm -rf myenv
