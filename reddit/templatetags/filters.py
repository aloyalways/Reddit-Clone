from django.template.defaulttags import register

@register.filter
def user_has_voted(el, user):
    return el.get_user_vote(user)