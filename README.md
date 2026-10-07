# HatsuboshiToolkit/Gakumas(Gakuen IdolMaster)

A modified fork for `学園アイドルマスター` from [vilebbit/HoshimiToolkit](https://github.com/vilebbit/HoshimiToolkit) `IDOLY PRIDE` components.

The `API` branch downloads game resources from Octo and exports game masterdb tables as YAML and JSON.

## Important Notice

***As a courtesy to other fans, please refrain from spoiling unreleased contents if any are found after decrypting.***

## How to use (Get Octo database from API)

1. Install the requirements at the repository root.

   ```sh
   pip install -r requirements.txt
   ```

2. Read the comments in config.ini and edit the args according to your needs.

3. Run `main.py --help` for usage.

   ```text
   Options:
     --mode [once|loop]                  Run once or check for updates continuously.
     --reset BOOLEAN                     Reset the local resource database.
     --init_download BOOLEAN             Download all resources on first use.
     --download_type [ALL|ab|resource]    Download all resources, AssetBundles only,
                                         or Resources only.
     --loop_interval INTEGER             Update interval in seconds (default: 600).
     --help                              Show help and exit.
   ```

   ```sh
   python main.py --mode once
   python main.py --mode loop --loop_interval 600
   ```
   The update data will make a copy in the folder named with database revision under cache/update if you set UPDATE_FLAG to True in config.ini, else it will only merge to default directory.

## How to use (Get game masterdb from API)

1. Install the package at the repository root.

   ```sh
   python -m pip install .
   ```

   Building the SQLCipher dependency requires a C compiler and SQLCipher development headers, such as `build-essential` and `libsqlcipher-dev` on Debian / Ubuntu.

2. Create an account file outside the repository.

   ```json
   {"refresh_token": "YOUR_REFRESH_TOKEN"}
   ```

   Keep the directory writable so refreshed tokens can be saved. Recommended permissions are `700` for the directory and `600` for the file.

3. Run the downloader.

   ```sh
   hatsuboshi-masterdb --credentials /private/account.json --output cache/masterdb
   ```
   Run `hatsuboshi-masterdb --help` for all options.

## Updating masterdb schemas

Generate `dump.cs` from your own game installation with Il2CppDumper, then run:

```sh
python -m pip install grpcio-tools
python scripts/export_master_proto.py --dump /private/dump.cs --game-version 3.4.1
```

Schema export requires Git and Docker to run the pinned campus Go analyser. Generated schemas are compiled before replacing the existing files. Check compatibility before using new schemas.

## Special Thanks

- [vilebbit/HoshimiToolkit](https://github.com/vilebbit/HoshimiToolkit)
- [vertesan/campus](https://github.com/vertesan/campus)
