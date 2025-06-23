# HatsuboshiToolkit/Gakumas(Gakuen IdolMaster)

## Important Notice

***As a courtesy to other fans, please refrain from spoiling unreleased contents if any are found after decrypting.***

## How to use (Get octo database from API)

1. Install the requirements at the root folder
    ```
    pip install -r requirements.txt
    ```

2. Read the comments in `config.ini` and edit the args according to your needs.  
   
3. Run `main.py --help` for usage.
    ```
    Usage: main.py [OPTIONS]

    Options:
    --reset BOOLEAN          Used to reset local database.
    --db_revision INTEGER    Set the database revision when reset.
    --init_download BOOLEAN  Whether to download the full resource on first use.
    --help                   Show this message and exit.
    ```
    ```
    python main.py --mode [once|loop]
    ```
    The commu txt files will store under the `cache/Resource` folder