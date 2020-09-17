# CommonPass Sample Resource Generator 
To get started, first clone the repo:

```
git clone https://github.com/the-commons-project/commonpass_sample_resources.git
```

## Initial setup
The scripts depend on the Python modules defined in `requirements.txt`, so you'll need to make sure that they are installed. The easiest way to do so would be to create and activate a virtual environment. You can use the following commands to do so:

```
python -m venv myenv
source myenv/bin/activate
```

Then, you can install the dependencies using the following command:

```
pip install -r requirements.txt
```

## Running the scripts
If you've set up a virtual environment, you will need to make sure it's active (e.g., `source myenv/bin/activate`). You can run the script using the following command:

```
python DSTU2.py smart_it_sandbox.json
```

`DSTU2.py` takes a config file as a parameter. If you specify `smart_it_sandbox.json` as the config file parameter, it will generate resources based on the options in the config file and store them in the SMART IT Sandbox (see the `unprotected_base_url` option in the config file). The script with output the patient ID of the newly created patient. You can use that patient ID when authorizing a SMART app in order to get access to the newly created resources. 



