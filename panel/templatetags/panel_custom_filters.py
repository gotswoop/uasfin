from django import template

register = template.Library()

# Checks if a username is a UAS panel member
# Returns True if username is a number and longer than 6 digits
@register.filter(is_safe=True)
def is_uas_panel_member(username):
    val = str(username)
    if len(val) > 6 and val.isdigit():
        return True
    else:
        return False

# https://djangosnippets.org/snippets/2718/
def increment_var(parser, token):

	parts = token.split_contents()
	if len(parts) < 2:
		raise template.TemplateSyntaxError("'increment' tag must be of the form:  {% increment <var_name> %}")
	return IncrementVarNode(parts[1])

register.tag('++', increment_var)

class IncrementVarNode(template.Node):

	def __init__(self, var_name):
		self.var_name = var_name

	def render(self,context):
		try:
			value = context[self.var_name]
			context[self.var_name] = value + 1
			return u""
		except:
			raise template.TemplateSyntaxError("The variable does not exist.")
