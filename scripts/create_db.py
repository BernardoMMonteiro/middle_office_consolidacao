#!/usr/bin/env python3
"""Cria um banco SQLite com as tabelas fundo, fic_master_map e movements.
Também pode popular com dados sintéticos (movimentações entre 11:00 e 15:00).
"""

import sqlite3, os, random
from datetime import datetime, timedelta

SCHEMA_SQL = '''
PRAGMA journal_mode = WAL;

DROP TABLE IF EXISTS movements;
DROP TABLE IF EXISTS fic_master_map;
DROP TABLE IF EXISTS fundo;

CREATE TABLE fundo (
  id INTEGER PRIMARY KEY,
  fundo_code TEXT NOT NULL,
  fundo_name TEXT NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('FIC','Master'))
);

CREATE TABLE fic_master_map (
  id INTEGER PRIMARY KEY,
  fic_id INTEGER NOT NULL,
  master_id INTEGER NOT NULL,
  FOREIGN KEY (fic_id) REFERENCES fundo(id),
  FOREIGN KEY (master_id) REFERENCES fundo(id)
);

CREATE TABLE movements (
  id_movimento INTEGER PRIMARY KEY,
  cotista TEXT NOT NULL,
  fic_id INTEGER NOT NULL,
  tipo TEXT NOT NULL CHECK (tipo IN ('Aplicacao','Resgate')),
  valor REAL NOT NULL,
  datahora_mov TEXT NOT NULL,
  FOREIGN KEY (fic_id) REFERENCES fundo(id)
);
'''


def seed_basic(conn):
    cur = conn.cursor()
    fundos = [
        (1, 'FIC_A', 'FIC A', 'FIC'),
        (2, 'FIC_B', 'FIC B', 'FIC'),
        (3, 'FIC_C', 'FIC C', 'FIC'),
        (4, 'Master_01', 'Master 01', 'Master'),
        (5, 'Master_02', 'Master 02', 'Master'),
    ]
    cur.executemany('INSERT INTO fundo (id, fundo_code, fundo_name, tipo) VALUES (?,?,?,?)', fundos)
    rel = [
        (1, 1, 4),
        (2, 2, 4),
        (3, 3, 5),
    ]
    cur.executemany('INSERT INTO fic_master_map (id, fic_id, master_id) VALUES (?,?,?)', rel)
    conn.commit()

def seed_movements(conn, rows: int, date_iso: str, rng: random.Random):
    """Gera movimentos sintéticos somente entre 11:00 e 15:00 no dia informado."""
    base = datetime.fromisoformat(date_iso + 'T11:00:00')
    end = datetime.fromisoformat(date_iso + 'T15:00:00')
    cur = conn.cursor()
    cotistas = ['Joao','Maria','Pedro','Ana','Carlos','Julia','Bruno','Paula','Lucas','Marina','Felipe']
    tipos = ['Aplicacao','Resgate']
    fic_ids = [1,2,3]
    idm = 0
    while idm < rows:
        ts = base + timedelta(seconds=rng.randint(0, int((end-base).total_seconds())))
        cot = rng.choice(cotistas)
        fic = rng.choice(fic_ids)
        tipo = rng.choice(tipos)
        # valores variados, 100 a 5000 com 6 casas
        val = round(rng.uniform(100, 5000), 6)
        idm += 1
        cur.execute('INSERT INTO movements (id_movimento,cotista,fic_id,tipo,valor,datahora_mov) VALUES (?,?,?,?,?,?)',
                    (idm, cot, fic, tipo, val, ts.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def main():
    
    db ='data/arx.db'
    rows=1000
    date ='2025-08-29'
    seed=123

    os.makedirs(os.path.dirname(db), exist_ok=True)

    rng = random.Random(seed)
    con = sqlite3.connect(db)
    try:
        con.executescript(SCHEMA_SQL)
        seed_basic(con)
        if rows > 0:
            seed_movements(con, rows, date, rng)
        print(f"Banco criado em {db} com {rows} movimentos em {date}.")
    finally:
        con.close()

if __name__ == '__main__':
    main()