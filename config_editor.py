import json
import wechat

class Config:
	def __init__(self, config_path, prompts_path):
		self.config_path = config_path
		self.config = json.load(open(config_path))
		self.prompts = json.load(open(prompts_path))

	def save(self):
		json.dump(self.config, open(self.config_path, 'w'), indent = 4, sort_keys = True)

	def edit(self, user):
		def visualize_menu(menu, prompts, user):
			message = []
			id_to_key = {}

			try:
				message.append('----- %s -----' % prompts['menu_title'])
			except KeyError:
				pass

			message.append('请输入你要修改的配置的编号:')
			message.append('0.(返回)')

			for (i, (key, value)) in enumerate(sorted(menu.items())):
				if isinstance(value, dict):
					assert 'menu_title' in prompts[key].keys()
					prompt = prompts[key]['menu_title']
				else:
					prompt = prompts[key]

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
