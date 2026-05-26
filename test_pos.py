import pandas as pd
df = pd.read_csv('data/processed/mvp_data.csv')

def get_position(row):
    gp = row['GP']
    if gp == 0: gp = 1 # avoid strict div by zero
    ast_pg = row['AST'] / gp
    reb_pg = row['REB'] / gp
    blk_pg = row['BLK'] / gp
    
    if ast_pg >= 5.0 or (ast_pg >= 3.5 and reb_pg < 5.0):
        return 'G'
    elif reb_pg >= 8.5 and blk_pg >= 1.0:
        return 'C'
    elif reb_pg >= 10.0 and ast_pg < 4.0:
        return 'C'
    else:
        # Fallback to forwards
        if reb_pg < 3.5 and ast_pg > 2.5:
            return 'G'
        if reb_pg > 7.0 and blk_pg > 1.2:
            return 'C'
        return 'F'

df['POS'] = df.apply(get_position, axis=1)
print(df.groupby('POS').size())
# Let's check some actual players
print(df[df['PLAYER_NAME'] == 'Shaquille O\'Neal']['POS'].value_counts())
print(df[df['PLAYER_NAME'] == 'Stephen Curry']['POS'].value_counts())
print(df[df['PLAYER_NAME'] == 'LeBron James']['POS'].value_counts())
print(df[df['PLAYER_NAME'] == 'Tim Duncan']['POS'].value_counts())
