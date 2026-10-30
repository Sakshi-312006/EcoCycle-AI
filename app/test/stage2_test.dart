import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/waste_segregation_screen.dart';

void main() {
  testWidgets('Screen 4: WasteSegregationScreen renders 2x2 grid, photo recognition & future scope',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteSegregationScreen(appState: appState),
    ));

    // Verify title and subtitle
    expect(find.text('Waste Segregation'), findsOneWidget);
    expect(find.text('Choose the right bin for your waste'), findsOneWidget);

    // Verify Photo Recognition section
    expect(find.text('AI Photo Recognition'), findsOneWidget);

    // Verify exact 2x2 grid for 4 statutory bins
    expect(find.text('Green Bin'), findsOneWidget);
    expect(find.text('Blue Bin'), findsOneWidget);
    expect(find.text('Yellow Bin'), findsOneWidget);
    expect(find.text('Red Bin'), findsOneWidget);

    expect(find.text('Organic / Wet'), findsOneWidget);
    expect(find.text('Dry / Recyclable'), findsOneWidget);
    expect(find.text('Hazardous'), findsOneWidget);
    expect(find.text('E-waste'), findsOneWidget);

    // Verify Did you know? card
    expect(find.text('Did you know?'), findsOneWidget);
    expect(find.textContaining('Proper segregation keeps our environment clean'), findsOneWidget);

    // Verify Future Scope box
    expect(find.text('Future Scope'), findsOneWidget);
    expect(find.textContaining('AI Waste Recognition'), findsOneWidget);
    expect(find.textContaining('Smart Disposal Guidance'), findsOneWidget);
    expect(find.textContaining('Camera-Based Recognition'), findsOneWidget);
  });

  testWidgets('Screen 4 -> BinCategoryDetailsScreen navigation & components',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteSegregationScreen(appState: appState),
    ));

    // Tap Green Bin card
    await tester.tap(find.text('Green Bin'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify details screen elements
    expect(find.text('What Belongs in This Bin'), findsOneWidget);
    expect(find.text('Disposal & Handling Guidelines'), findsOneWidget);
    expect(find.text("Simple Do's and Don'ts"), findsOneWidget);
    expect(find.text("DO'S"), findsOneWidget);
    expect(find.text("DON'TS"), findsOneWidget);
    expect(find.text('Report Green Bin Waste'), findsOneWidget);
  });

  testWidgets('Photo Recognition Future Scope modal opens on tap',
      (WidgetTester tester) async {
    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: WasteSegregationScreen(appState: appState),
    ));

    // Tap the AI Photo Recognition section
    await tester.tap(find.text('AI Photo Recognition'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify 4-step workflow modal
    expect(find.text('Target AI Classification Workflow:'), findsOneWidget);
    expect(find.text('Got it'), findsOneWidget);
  });
}
