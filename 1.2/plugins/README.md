### Contrib plugins for PyLink 1.2

#### cloudflare.py
- Cloudflare plugin: Allows manipulating DNS entries for a network.
    - requires [python-cloudflare](https://github.com/cloudflare/python-cloudflare) -> (`pip3 install cloudflare`)
    - commands include `cf-add`, `cf-show`, `cf-rem`, `pool`, and `depool`
    - permissions are in the form `cloudflare.COMMAND`
    - configuration options are read from a `cloudflare:` config block, which has the following options:
        * `target_zone`: The [zone ID](https://blog.cloudflare.com/cloudflare-tips-frequently-used-cloudflare-ap/) the plugin should operate on.
        * `api_email`: Your account email.
        * `api_key`: The account's API token.

#### hashpass.py
- hashpass plugin: Allows for hashing of arbitrary passwords via supported algorithms

#### mimic.py
- Mimic plugin: Echoes ZNC (energymech)-format chatlogs to channels by spawning fake users and talking as them. Useful for training AI bots and the like.

#### passgen.py
- Passgen plugin: Generates passwords/random strings given inputted criteria
    - requires `StringGenerator` (`pip3 install StringGenerator`)
