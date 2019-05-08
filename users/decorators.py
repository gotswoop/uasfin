from fin.models import User_Actions

def log_password_reset(func):
	def wrap(request, *args, **kwargs):
		print("IN MEAW")
		print(type(request.user))
		print(request.META['REMOTE_ADDR'])
		new_item = User_Actions.objects.create(
			user_id = request.user, 
			user_ip = request.META['REMOTE_ADDR'],
			action = "Profile",
		)
		return func(request, *args, **kwargs)
	return wrap

def pretty_request(request):
    headers = ''
    for header, value in request.META.items():
        if not header.startswith('HTTP'):
            continue
        header = '-'.join([h.capitalize() for h in header[5:].lower().split('_')])
        headers += '{}: {}\n'.format(header, value)

    return (
        '{method} HTTP/1.1\n'
        'Content-Length: {content_length}\n'
        'Content-Type: {content_type}\n'
        '{headers}\n\n'
        '{body}'
    ).format(
        method=request.method,
        content_length=request.META['CONTENT_LENGTH'],
        content_type=request.META['CONTENT_TYPE'],
        headers=headers,
        body=request.body,
    )