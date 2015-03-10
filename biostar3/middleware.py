from __future__ import absolute_import, division, print_function, unicode_literals
import logging

from django.contrib import messages
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponsePermanentRedirect as Redirect
from biostar3.forum.models import UserGroup
from django.contrib.sites.models import Site
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

# Get current site
User = get_user_model()

logger = logging.getLogger("biostar")

SITE = Site.objects.get_current()

# Loads this group when none are specified.
DEFAULT_GROUP = UserGroup.objects.filter(name=settings.DEFAULT_GROUP_NAME).first()

class AutoSignupAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):

        # This social login already exists.
        if sociallogin.is_existing:
            return

        try:

            # The provider that produces the login
            provider_id = sociallogin.account.get_provider().id

            # Check if we could/should connect it.
            email = sociallogin.account.extra_data.get('email')

            logger.info("connecting %s with %s" % (email, provider_id))

            # Try to get the verification for the account
            verified = sociallogin.account.extra_data.get('verified_email')

            # We will trust some social account providers with the email information.
            verified = verified or (provider_id in settings.TRUSTED_SOCIALACCOUNT_PROVIDERS)

            if email:
                user = User.objects.get(email=email)
                if verified:
                    sociallogin.connect(request, user)
                else:
                    msg = "Attempt to log with email from non verified provider!"
                    logger.error(msg)
                    raise Exception(msg)

        except User.DoesNotExist:
            pass

class GlobalMiddleware(object):
    """Performs tasks that are applied on every request"""

    def process_request(self, request):

        # Ensures that requests have all the information needed.
        user = request.user
        if not user.is_authenticated():
            user.is_moderator = user.is_admin = False

        # Set the group based on subdomain on the current request
        subdomain = settings.GET_SUBDOMAIN(request)
        if subdomain in settings.DEFAULT_SUBDOMAINS:
            group = DEFAULT_GROUP
        else:
            group = UserGroup.objects.filter(domain__iexact=subdomain).first()
            if not group:
                url = "%s://%s" % (request.scheme, SITE.domain)
                return Redirect(url)

        # Groups need to be set on each request.
        request.group = group

