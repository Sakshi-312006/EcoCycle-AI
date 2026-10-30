import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/localization/app_localizations.dart';
import 'package:ecocycle_ai/screens/home_screen.dart';
import 'package:ecocycle_ai/screens/profile_settings_screen.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Three-line menu icon navigates to ProfileSettingsScreen', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(appState: appState),
    ));
    await tester.pump();

    // Verify menu button exists
    final menuButton = find.byIcon(Icons.menu_rounded);
    expect(menuButton, findsOneWidget);

    // Tap the menu button
    await tester.tap(menuButton);
    await tester.pumpAndSettle();

    // Verify ProfileSettingsScreen is pushed
    expect(find.byType(ProfileSettingsScreen), findsOneWidget);
  });

  testWidgets('Language selection updates AppState and translates dictionary strings', (WidgetTester tester) async {
    final appState = AppState();

    // Default: English
    expect(appState.language, 'en');
    var loc = AppLocalizations(appState.language);
    expect(loc.translate('navHome'), 'Home');
    expect(loc.translate('marketplaceTitle'), 'Circular Marketplace');

    // Switch to Hindi
    await appState.setLanguage('hi');
    loc = AppLocalizations(appState.language);
    expect(loc.translate('navHome'), 'होम');
    expect(loc.translate('helloUser'), 'नमस्ते');
    expect(loc.translate('marketplaceTitle'), 'चक्रीय बाज़ार');

    // Switch to Marathi
    await appState.setLanguage('mr');
    loc = AppLocalizations(appState.language);
    expect(loc.translate('navHome'), 'मुख्यपृष्ठ');
    expect(loc.translate('helloUser'), 'नमस्कार');
    expect(loc.translate('marketplaceTitle'), 'चक्रीय बाजारपेठ');

    // Switch to Kannada
    await appState.setLanguage('kn');
    loc = AppLocalizations(appState.language);
    expect(loc.translate('navHome'), 'ಮುಖಪುಟ');
    expect(loc.translate('helloUser'), 'ನಮಸ್ಕಾರ');
    expect(loc.translate('marketplaceTitle'), 'ಮರುಬಳಕೆ ಮಾರುಕಟ್ಟೆ');

    // Switch to Tamil
    await appState.setLanguage('ta');
    loc = AppLocalizations(appState.language);
    expect(loc.translate('navHome'), 'முகப்பு');
    expect(loc.translate('helloUser'), 'வணக்கம்');
    expect(loc.translate('marketplaceTitle'), 'மறுபயன்பாட்டு சந்தை');

    // Switch to Telugu
    await appState.setLanguage('te');
    loc = AppLocalizations(appState.language);
    expect(loc.translate('navHome'), 'హోమ్');
    expect(loc.translate('helloUser'), 'నమస్కారం');
    expect(loc.translate('marketplaceTitle'), 'పునర్వినియోగ మార్కెట్');
  });

  testWidgets('Language selector bottom sheet displays all 6 languages', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(appState: appState),
    ));
    await tester.pump();

    // Find language selector badge
    final langSelector = find.byIcon(Icons.language_rounded);
    expect(langSelector, findsOneWidget);

    // Tap language selector
    await tester.tap(langSelector);
    await tester.pumpAndSettle();

    // Verify all 6 languages are rendered in the bottom sheet
    expect(find.text('English (EN)'), findsOneWidget);
    expect(find.text('हिन्दी (Hindi)'), findsOneWidget);
    expect(find.text('मराठी (Marathi)'), findsOneWidget);
    expect(find.text('ಕನ್ನಡ (Kannada)'), findsOneWidget);
    expect(find.text('தமிழ் (Tamil)'), findsOneWidget);
    expect(find.text('తెలుగు (Telugu)'), findsOneWidget);
  });
}
