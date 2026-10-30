import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/core/constants.dart';
import 'package:ecocycle_ai/main.dart';
import 'package:ecocycle_ai/screens/home_screen.dart';

void main() {
  testWidgets('EcoCycleApp smoke test - splash screen renders brand', (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(EcoCycleApp(appState: appState));

    // Verify app brand is rendered
    expect(find.text(AppConstants.appName), findsOneWidget);
    expect(find.text(AppConstants.appTagline), findsOneWidget);

    // Advance timer so splash transition completes cleanly
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
  });

  testWidgets('HomeScreen renders approved reference design and no legacy pillars', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(appState: appState),
    ));
    await tester.pump();

    // Verify Greeting
    expect(find.text('Hello, Sakshi!'), findsOneWidget);
    expect(find.text('Together for a cleaner, greener tomorrow.'), findsOneWidget);

    // Verify Impact Banner
    expect(find.text('Small actions'), findsOneWidget);
    expect(find.text('make a big impact!'), findsOneWidget);

    // Verify 4 Pastel Feature Cards
    expect(find.text('Waste Segregation'), findsOneWidget);
    expect(find.text('Sort waste the right way'), findsOneWidget);
    expect(find.text('Report Waste'), findsOneWidget);
    expect(find.text('Inform & get it collected'), findsOneWidget);
    expect(find.text('Circular Marketplace'), findsOneWidget);
    expect(find.text('Buy, sell or give away'), findsOneWidget);
    expect(find.text('Construction Debris'), findsOneWidget);
    expect(find.text('Manage debris responsibly'), findsOneWidget);

    // Verify Bottom Wide Banner
    expect(find.text('Reduce'), findsOneWidget);
    expect(find.text('Reuse'), findsOneWidget);
    expect(find.text('Recycle'), findsOneWidget);

    // Verify legacy components are strictly absent
    expect(find.text('Pillar 1'), findsNothing);
    expect(find.text('Pillar 2'), findsNothing);
    expect(find.text('Pillar 3'), findsNothing);
    expect(find.text('Pillar 4'), findsNothing);
    expect(find.text('CIVIC TIER: GOLD'), findsNothing);
  });
}
