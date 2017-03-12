Community contributed modules for PyLink.

#### hashpass.py
- hashpass plugin: Allows for hashing of arbitrary passwords via supported algorithms

#### mimic.py
- Mimic plugin: Echoes ZNC (energymech)-format chatlogs to channels by spawning fake users and talking as them. Useful for training AI bots and the like.

#### passgen.py
- Passgen plugin: Generates passwords/random strings given inputted criteria
    - requires `StringGenerator` (`pip3 install StringGenerator`)

#### cloudflare.py
- Cloudflare plugin: Allows manipulating DNS entries for a network.
    - requires 'cloudflare' -> (`pip3 install cloudflare`)
    - commands include add, show, rem, pool, depool
    - permissions are in the form cloudflare.COMMAND
    - configuration options include:
        * `target_zone`: The zone the plugin should operate on.
        * `api_email`: The email that owns `target_zone`.
        * `api_key`: The account's API token.