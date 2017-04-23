import json
import wechat

class Config:
	def __init__(self, config_path, prompts_path):
		'''
		config_path: file path of configuration file
		prompts_path: file path of prompts
		'''
		self.config_path = config_path

		# Load files
		self.config = json.load(open(config_path, encoding = 'utf-8'))
		self.prompts = json.load(open(prompts_path, encoding = 'utf-8'))

	def save(self):
		'''
		Save configuration to file
		'''
		json.dump(self.config, open(self.config_path, 'w'), indent = 4, sort_keys = True)

	def edit(self, user):
		'''
		Let the user to edit configuration.

		user: a 'WechatUser' object
		'''
		def visualize_menu(menu, prompts, user):
			message = []
			id_to_key = {} # Map from menu item id to key in the dictionary

			# Menu title
			try:
				message.append('----- %s -----' % prompts['menu_title'])
			except KeyError:
				pass

			# Prompt
			message.append('请输入你要修改的配置的编号:')
			message.append('0.(返回)')

			# Add each menu item to the message
			for (i, (key, value)) in enumerate(sorted(menu.items())):
				# Get prompt for this item
				if isinstance(value, dict):
					assert 'menu_title' in prompts[key].keys()
					prompt = prompts[key]['menu_title']
				else:
					prompt = prompts[key]

				# Add item value to the prompt
				if isinstance(value, bool):
					if value == True:
						content = '%s: 是' % prompt
					else:
						content = '%s: 否' % prompt
				elif isinstance(value, int):
					content = '%s: %d' % (prompt, value)
				elif isinstance(value, dict):
					content = prompt
				else:
					raise Exception()

				# Update result
				message.append('%d.%s' % (i+1, content))
				id_to_key[i+1] = key

			user.send_message('\n'.join(message))

			return id_to_key

		def edit_menu(menu, prompts, user):
			while True:
				id_to_key = visualize_menu(menu, prompts, user)
				
				selection = user.get_int('', 0, len(menu.keys()) + 1)

				if selection == 0:
					return

				key = id_to_key[selection]
				value = menu[key]
				prompt = prompts[key]

				if isinstance(value, bool):
					menu[key] = not menu[key]
				elif isinstance(value, int):
					menu[key] = user.get_int('请输入%s' % prompt, 0)
				elif isinstance(value, dict):
					edit_menu(value, prompts[key], user)
				else:
					raise Exception()

		edit_menu(self.config, self.prompts, user)
		self.save()
		user.send_message('已保存配置')

	def __call__(self, path):
		cursor = self.config
		for key in path.split('/'):
			cursor = cursor[key]
		return cursor
