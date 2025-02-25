ANDROID_BUILD_DIR=android_kivy_build

android-build-debug:
	rm -rf $(ANDROID_BUILD_DIR)
	mkdir $(ANDROID_BUILD_DIR)
	cp *.py $(ANDROID_BUILD_DIR)
    # have i mentioned recently how much i hate kivy?
	mv $(ANDROID_BUILD_DIR)/kivy_app.py $(ANDROID_BUILD_DIR)/main.py
	cp *.kv $(ANDROID_BUILD_DIR)
	cp m821bt.ttf $(ANDROID_BUILD_DIR)
	cp buildozer.spec $(ANDROID_BUILD_DIR)
	cd $(ANDROID_BUILD_DIR) && ln -s ../.buildozer ./
	cd $(ANDROID_BUILD_DIR) && buildozer --verbose android debug

android-deploy-debug:
	cd $(ANDROID_BUILD_DIR) && buildozer --verbose android deploy

