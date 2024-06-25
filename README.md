# HatsuboshiToolkit/Gakumas(Gakuen IdolMaster)

## First things first

***As a courtesy to other fans, please refrain from spoiling unreleased contents if any are found after decrypting.***

## How to use (Get octo database from API)

1. Install the requirements at the root folder
    ```
    pip install -r requirements.txt
    ```

2. Read the comments in `config.ini` and edit the args according to your needs.  
   
3. Run `main.py --help` for usage.
    ```
    python main.py --mode [once|loop]
    ```
    The update data will make a copy in the folder named with database revision under `cache/update` if you set `UPDATE_FLAG` to `True` in `config.ini`, else it will only merge to default directory.