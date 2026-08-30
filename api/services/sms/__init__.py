"""SMS sending — provider abstraction, French A2P rules and pure helpers.

The SMS channel is a RELANCE channel: it re-contacts a prospect who did not
react to the cold email, pushing them back to their demo link. See the Asana
« SMS v1 » ticket for the full scoping. Everything provider-specific lives
behind :class:`~services.sms.sms_provider.SmsProvider` so a switch away from
smsmode is a one-file change.
"""
