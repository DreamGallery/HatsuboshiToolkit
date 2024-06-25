# HatsuboshiToolkit/Gakumas(Gakuen IdolMaster)
A modified fork for `学園アイドルマスター` from [MalitsPlus/HoshimiToolkit](https://github.com/MalitsPlus/HoshimiToolkit) `IDOLY PRIDE` components.

## First things first

***As a courtesy to other fans, please refrain from spoiling unreleased contents if any are found after decrypting.***

## How to use

1. Install the requirements at the root folder
    ```
    pip install -r requirements.txt
    ```
2. Copy your `octocacheevai` into `cache/` folder. You can get the `octocacheevai` under
   ```
   /data_mirror/data_ce/null/0/com.bandainamcoent.idolmaster_gakuen/files/octo/pdb/400/205000/
   ```
    from your root enabled device or emulator.  

3. Read the comments in `config.ini` and edit the args according to your needs.  
   
4. Run `main.py`.
    ```
    python main.py
    ```
    The update data will make a copy in the folder named with the database revision under `cache/update` if you set `UPDATE_FLAG` to `True` in `config.ini`, else it will only merge to default directory.


## Get update from API
If you don't want to go through files but want to get updates through api, you can use `API` branch.  

Switch to `API` branch 
```
git checkout API
```
※ Please do not abuse API

## Special Thanks
[MalitsPlus/HoshimiToolkit](https://github.com/MalitsPlus/HoshimiToolkit)